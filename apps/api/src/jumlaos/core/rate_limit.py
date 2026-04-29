"""Global rate limiting (F10 / F20).

Single Redis-backed slowapi ``Limiter`` shared by the whole app. Per-route
limits are applied via ``@limiter.limit(...)`` decorators on the route
handlers. Webhook routes bypass user-keyed limits and use IP+HMAC instead.

Per-endpoint policies the audit calls out:
* ``POST /v1/auth/otp/request`` — 1/min per phone, 5/min per IP
* ``POST /v1/auth/otp/verify``  — 5/min per phone, 30/min per IP
* ``POST /v1/auth/refresh``     — 6/min per user
* ``POST /v1/webhook/whatsapp`` — 100/sec per IP (HMAC required separately)

Falls back to in-memory storage in dev when ``redis_url`` is unset.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import ORJSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import Response

from jumlaos.config import get_settings
from jumlaos.shared.phone import PhoneError, normalize_ma


def _phone_from_request(request: Request) -> str:
    """Best-effort phone extractor for OTP routes.

    Reads the raw JSON body once and stashes it on ``request.state`` so the
    handler can re-read without paying for a second body parse. The phone is
    normalized to E.164 before keying so that varying input formats of the
    same number share one rate-limit bucket; on parse failure the limiter
    falls back to the IP address — never silently let a request through
    unkeyed.
    """
    cached: dict[str, object] | None = (
        request.state.json_body if hasattr(request.state, "json_body") else None
    )
    if cached is None:
        # We cannot read async body in a sync slowapi key func; rely on the
        # middleware to populate request.state.json_body before routing.
        return get_remote_address(request)
    phone = cached.get("phone") if isinstance(cached, dict) else None
    if isinstance(phone, str) and phone:
        try:
            return f"phone:{normalize_ma(phone)}"
        except PhoneError:
            pass
    return get_remote_address(request)


def _user_id_from_request(request: Request) -> str:
    """Resolve the authenticated user id for limits keyed per user.

    Tries the access cookie first, then the refresh cookie (so /refresh —
    which has no access cookie when the access token has expired — still
    keys on user, not on the unauthenticated IP).
    """
    from jumlaos.core.security import decode_token

    user_id = request.state.user_id if hasattr(request.state, "user_id") else None
    if user_id is not None:
        return f"user:{user_id}"

    for cookie_name, expected in (("jumlaos_access", "access"), ("jumlaos_refresh", "refresh")):
        token = request.cookies.get(cookie_name)
        if not token:
            continue
        try:
            payload = decode_token(token, expected_type=expected)
        except Exception:  # noqa: S112 — fall back to IP key on any decode failure
            continue
        sub = payload.get("sub")
        if sub:
            return f"user:{sub}"

    return get_remote_address(request)


def _build_storage_uri() -> str:
    settings = get_settings()
    if settings.redis_url:
        return settings.redis_url
    return "memory://"


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_build_storage_uri(),
    headers_enabled=True,
    strategy="fixed-window",
)


def rate_limit_exceeded_handler(request: Request, exc: Exception) -> Response:
    detail = "rate_limited"
    if isinstance(exc, RateLimitExceeded):
        detail = f"rate_limited: {exc.detail}"
    return ORJSONResponse(
        status_code=429,
        content={"error": {"code": "rate_limited", "detail": detail}},
    )


# Key functions exposed for @limiter.limit(..., key_func=...).
phone_key = _phone_from_request
ip_key = get_remote_address
user_key = _user_id_from_request


async def cache_json_body_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Cache the JSON body on ``request.state.json_body`` for OTP routes.

    slowapi key functions are sync and cannot await ``request.json()``. We
    pre-read the body once for OTP endpoints, then replay it for downstream
    handlers via ``request._body`` (Starlette caches this internally).
    """
    if request.url.path in ("/v1/auth/otp/request", "/v1/auth/otp/verify"):
        try:
            raw = await request.body()
            request.state.json_body = json.loads(raw or b"{}")
        except (ValueError, json.JSONDecodeError):
            request.state.json_body = {}
    return await call_next(request)
