"""Procrastinate worker entrypoint.

Run locally:
    uv run python -m jumlaos.workers.entrypoint
"""

from __future__ import annotations

import asyncio

from jumlaos.config import get_settings
from jumlaos.logging import configure_logging, get_logger


async def main() -> None:
    configure_logging()
    log = get_logger("jumlaos.worker")
    settings = get_settings()
    log.info("worker_starting", env=settings.env)
    # The real Procrastinate app lives in jumlaos.workers.app (not yet wired).
    # Keep this skeleton awake for deploy-health checks.
    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
