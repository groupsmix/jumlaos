"""Idempotency middleware (F02 + F15).

Mutating requests carrying an ``Idempotency-Key`` header are deduplicated
against the ``idempotency_keys`` table.

Design:

* The unique scope is ``(business_id, user_id, idempotency_key)``. Pre-auth
  callers use ``business_id=0, user_id=0`` so two anonymous callers cannot
  collide on the same key.
* Insert-then-conflict, *not* SELECT-then-INSERT — Postgres
  ``ON CONFLICT DO NOTHING RETURNING`` makes the check race-free.
* When the row already exists with ``status='completed'``, we replay the
  stored ``response_status`` + ``response_body`` and skip the handler.
* When the row exists with ``status='pending'`` (concurrent in-flight retry),
  we 409 instead of running the handler twice.
* On handler error we mark the row ``status='failed'`` — we do *not* delete
  it. Callers that retry the same key get a deterministic 409 until they
  rotate the key.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import ORJSONResponse
from sqlalchemy import text
from starlette.responses import Response

from jumlaos.core.db import get_sessionmaker
from jumlaos.core.security import decode_token

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
ACCESS_COOKIE = "jumlaos_access"


def _resolve_scope(request: Request) -> tuple[int, int]:
    """Best-effort extraction of (business_id, user_id) from the access token.

    Failures fall back to ``(0, 0)`` (anonymous). The middleware runs before
    auth dependencies, so a malformed or missing token is expected for
    pre-login routes (``/v1/auth/otp/...``).
    """
    token = request.cookies.get(ACCESS_COOKIE)
    if token is None:
        auth = request.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
    if not token:
        return 0, 0
    try:
        payload = decode_token(token, expected_type="access")
    except Exception:
        return 0, 0
    try:
        return int(payload.get("bid", 0) or 0), int(payload.get("sub", 0) or 0)
    except (TypeError, ValueError):
        return 0, 0


async def idempotency_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    idem_key = request.headers.get("idempotency-key")
    if not idem_key or request.method not in MUTATING_METHODS:
        return await call_next(request)

    business_id, user_id = _resolve_scope(request)
    sessionmaker = get_sessionmaker()

    # 1. Race-free claim using INSERT ... ON CONFLICT DO NOTHING RETURNING id.
    async with sessionmaker() as session:
        row = (
            await session.execute(
                text(
                    """
                    INSERT INTO idempotency_keys
                        (business_id, user_id, idempotency_key, method, path, status)
                    VALUES
                        (:bid, :uid, :k, :m, :p, 'pending')
                    ON CONFLICT (business_id, user_id, idempotency_key)
                    DO NOTHING
                    RETURNING id
                    """
                ),
                {
                    "bid": business_id,
                    "uid": user_id,
                    "k": idem_key,
                    "m": request.method,
                    "p": request.url.path[:255],
                },
            )
        ).first()
        await session.commit()

        if row is None:
            # Key already claimed. Look up its current status / stored response.
            existing = (
                await session.execute(
                    text(
                        """
                        SELECT status, response_status, response_body
                        FROM idempotency_keys
                        WHERE business_id = :bid AND user_id = :uid AND idempotency_key = :k
                        """
                    ),
                    {"bid": business_id, "uid": user_id, "k": idem_key},
                )
            ).first()
            if existing is None:
                # Theoretically impossible (we just lost the INSERT race), but
                # treat as a transient conflict.
                return ORJSONResponse(
                    status_code=409,
                    content={"error": {"code": "idempotency_concurrent_request"}},
                )
            status, resp_status, resp_body = existing
            if status == "completed" and resp_status is not None:
                return ORJSONResponse(status_code=resp_status, content=resp_body)
            if status == "failed":
                return ORJSONResponse(
                    status_code=409,
                    content={"error": {"code": "idempotency_key_failed"}},
                )
            # status == 'pending' → in-flight duplicate.
            return ORJSONResponse(
                status_code=409,
                content={"error": {"code": "idempotency_concurrent_request"}},
            )

    # 2. Run the handler. Capture its response so we can persist it.
    try:
        response = await call_next(request)
    except Exception:
        async with sessionmaker() as session:
            await session.execute(
                text(
                    """
                    UPDATE idempotency_keys SET status = 'failed', updated_at = now()
                    WHERE business_id = :bid AND user_id = :uid AND idempotency_key = :k
                    """
                ),
                {"bid": business_id, "uid": user_id, "k": idem_key},
            )
            await session.commit()
        raise

    # 3. Persist completed response so a retry of the same key returns
    #    the same answer instead of executing the handler again.
    body_bytes = b""
    async for chunk in response.body_iterator:  # type: ignore[attr-defined]
        body_bytes += chunk
    try:
        body_json = json.loads(body_bytes) if body_bytes else None
    except json.JSONDecodeError:
        body_json = None

    async with sessionmaker() as session:
        await session.execute(
            text(
                """
                UPDATE idempotency_keys
                SET status = 'completed',
                    response_status = :rs,
                    response_body = CAST(:rb AS JSONB),
                    updated_at = now()
                WHERE business_id = :bid AND user_id = :uid AND idempotency_key = :k
                """
            ),
            {
                "bid": business_id,
                "uid": user_id,
                "k": idem_key,
                "rs": response.status_code,
                "rb": json.dumps(body_json) if body_json is not None else None,
            },
        )
        await session.commit()

    # Rebuild the response so downstream middleware sees the body bytes we read.
    return Response(
        content=body_bytes,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type,
    )
