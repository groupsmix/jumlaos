"""Health + readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from jumlaos import __version__
from jumlaos.core.deps import db

router = APIRouter()


@router.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@router.get("/ready", include_in_schema=False)
async def ready(session: AsyncSession = Depends(db)) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ready"}
