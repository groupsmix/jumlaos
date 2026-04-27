from fastapi import Request
from fastapi.responses import ORJSONResponse

from jumlaos.core.db import get_sessionmaker


async def idempotency_middleware(request: Request, call_next):
    idem_key = request.headers.get("idempotency-key")
    if not idem_key or request.method not in ("POST", "PATCH", "DELETE", "PUT"):
        return await call_next(request)

    async_session = get_sessionmaker()

    # 1. Check if key exists
    async with async_session() as session:
        from sqlalchemy import text

        res = await session.execute(
            text(
                "SELECT response_status, response_body FROM idempotency_keys WHERE idempotency_key = :k"
            ),
            {"k": idem_key},
        )
        row = res.fetchone()
        if row:
            status, body = row
            if status is None:
                return ORJSONResponse(status_code=409, content={"detail": "concurrent_request"})
            return ORJSONResponse(status_code=status, content=body)

        # Insert pending
        await session.execute(
            text("INSERT INTO idempotency_keys (idempotency_key, user_id) VALUES (:k, 0)"),
            {"k": idem_key},
        )
        await session.commit()

    # 2. Process request
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        # if error, we might delete the idempotency key so they can retry
        async with async_session() as session:
            from sqlalchemy import text
            await session.execute(text("DELETE FROM idempotency_keys WHERE idempotency_key = :k"), {"k": idem_key})
            await session.commit()
        raise e
