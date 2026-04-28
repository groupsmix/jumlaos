"""Health + readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from jumlaos.core.deps import db

router = APIRouter(tags=["ops"])


@router.get("/livez", status_code=200)
async def livez() -> dict[str, str]:
    """Liveness probe.

    Returns 200 immediately if the event loop is running.
    """
    return {"status": "alive"}


@router.get("/readyz", status_code=200)
async def readyz(session: AsyncSession = Depends(db)) -> dict[str, str]:
    """Readiness probe.

    Returns 200 if the app is ready to serve traffic. Checks DB connectivity.
    (Future: check Redis connectivity here too).
    """
    # Check DB
    await session.execute(text("SELECT 1"))

    # Check Redis (stub for when redis is actually wired)
    # await redis.ping()

    return {"status": "ready"}
