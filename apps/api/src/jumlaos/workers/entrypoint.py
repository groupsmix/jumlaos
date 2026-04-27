"""Procrastinate worker entrypoint.

Run locally:
    uv run python -m jumlaos.workers.entrypoint
"""

from __future__ import annotations

import asyncio

from jumlaos.config import get_settings
from jumlaos.logging import configure_logging, get_logger
from jumlaos.workers.app import app


async def main() -> None:
    configure_logging()
    log = get_logger("jumlaos.worker")
    settings = get_settings()
    log.info("worker_starting", env=settings.env)
    
    async with app.open_async():
        await app.run_worker_async()


if __name__ == "__main__":
    asyncio.run(main())
