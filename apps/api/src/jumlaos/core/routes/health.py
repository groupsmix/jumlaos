"""Health + readiness endpoints (F14).

* ``/v1/livez``  — process up, event loop responsive. Cheap.
* ``/v1/readyz`` — DB + Redis + Procrastinate jobs table + R2 reachable
  within 500 ms each, otherwise 503.

The readiness checks short-circuit on the first failure but still report
which dependency was responsible so dashboards can attribute outages.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Literal, cast

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from jumlaos.config import get_settings
from jumlaos.core.deps import db
from jumlaos.logging import get_logger

router = APIRouter(tags=["ops"])
log = get_logger("jumlaos.health")

_DEPENDENCY_TIMEOUT_S = 0.5


@router.get("/livez", status_code=200)
async def livez() -> dict[str, str]:
    """Liveness probe — returns 200 if the event loop is responsive."""
    return {"status": "alive"}


async def _with_timeout(
    name: str, coro_factory: Callable[[], Awaitable[None]]
) -> tuple[str, Literal["ok", "timeout", "error"], int]:
    started = time.perf_counter()
    try:
        await asyncio.wait_for(coro_factory(), timeout=_DEPENDENCY_TIMEOUT_S)
    except TimeoutError:
        return name, "timeout", int((time.perf_counter() - started) * 1000)
    except Exception as exc:
        log.warning("readyz_dependency_failed", dependency=name, error=str(exc))
        return name, "error", int((time.perf_counter() - started) * 1000)
    return name, "ok", int((time.perf_counter() - started) * 1000)


async def _check_postgres(session: AsyncSession) -> None:
    await session.execute(text("SELECT 1"))


async def _check_procrastinate(session: AsyncSession) -> None:
    """1-row read against the Procrastinate jobs table.

    Confirms the worker schema is present and reachable. ``LIMIT 1`` is
    cheap on any table size.
    """
    await session.execute(text("SELECT 1 FROM procrastinate_jobs LIMIT 1"))


async def _check_redis() -> None:
    settings = get_settings()
    if not settings.redis_url:
        return
    # Imported here so the module is optional in dev environments.
    from redis.asyncio import Redis

    client = Redis.from_url(settings.redis_url, socket_timeout=_DEPENDENCY_TIMEOUT_S)
    try:
        # redis-py's stubs declare ``ping()`` as ``Awaitable[bool] | bool``
        # because the same class is used for sync + async. The async variant
        # always returns an awaitable.
        await cast("Awaitable[bool]", client.ping())
    finally:
        await client.aclose()


async def _check_r2() -> None:
    settings = get_settings()
    if not settings.r2_endpoint or not settings.r2_bucket:
        return
    url = f"{settings.r2_endpoint.rstrip('/')}/{settings.r2_bucket}"
    async with httpx.AsyncClient(timeout=_DEPENDENCY_TIMEOUT_S) as client:
        resp = await client.head(url)
        if resp.status_code >= 500:
            raise RuntimeError(f"r2 head returned {resp.status_code}")


async def _check_db_pair(
    session: AsyncSession,
) -> list[tuple[str, Literal["ok", "timeout", "error"], int]]:
    """Run the two DB-bound checks sequentially.

    ``AsyncSession`` is not safe for concurrent use from multiple
    coroutines (its connection/transaction state can corrupt under
    interleaved ``await session.execute(...)`` calls), so the postgres
    and procrastinate probes share one session in series rather than
    racing through ``asyncio.gather``.
    """
    return [
        await _with_timeout("postgres", lambda: _check_postgres(session)),
        await _with_timeout("procrastinate", lambda: _check_procrastinate(session)),
    ]


@router.get("/readyz")
async def readyz(session: AsyncSession = Depends(db)) -> dict[str, object]:
    """Readiness probe — DB + Procrastinate + Redis + R2.

    Returns 200 only when all configured dependencies respond inside
    500 ms each. Returns 503 with per-dependency status otherwise.
    """
    db_results, redis_result, r2_result = await asyncio.gather(
        _check_db_pair(session),
        _with_timeout("redis", _check_redis),
        _with_timeout("r2", _check_r2),
    )
    results = [*db_results, redis_result, r2_result]
    statuses = {name: status for name, status, _ms in results}
    timings = {name: ms for name, _status, ms in results}
    all_ok = all(s == "ok" for s in statuses.values())
    if not all_ok:
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "dependencies": statuses, "ms": timings},
        )
    return {"status": "ready", "dependencies": statuses, "ms": timings}
