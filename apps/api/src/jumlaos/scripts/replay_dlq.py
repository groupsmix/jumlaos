"""F26: CLI for replaying webhook DLQ entries.

Usage:
    python -m jumlaos.scripts.replay_dlq --since 2026-01-01
    python -m jumlaos.scripts.replay_dlq --id 42
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime

from jumlaos.logging import get_logger

log = get_logger("jumlaos.scripts.replay_dlq")


async def _replay_by_id(dlq_id: int) -> None:
    from jumlaos.workers.tasks import replay_dlq

    await replay_dlq.defer_async(dlq_id=dlq_id)
    log.info("dlq_replay_enqueued", dlq_id=dlq_id)


async def _replay_since(since: str) -> None:
    from sqlalchemy import text

    from jumlaos.workers.context import with_business_context
    from jumlaos.workers.tasks import replay_dlq

    since_dt = datetime.fromisoformat(since)
    async with with_business_context("system") as session:
        rows = (
            await session.execute(
                text(
                    "SELECT id FROM webhook_dlq "
                    "WHERE resolved_at IS NULL AND received_at >= :since "
                    "ORDER BY id"
                ),
                {"since": since_dt},
            )
        ).all()

    count = 0
    for row in rows:
        await replay_dlq.defer_async(dlq_id=row.id)
        count += 1

    log.info("dlq_replay_batch_enqueued", count=count, since=since)


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay webhook DLQ entries")
    parser.add_argument("--id", type=int, help="Replay a single DLQ entry by ID")
    parser.add_argument("--since", type=str, help="Replay all unresolved entries since YYYY-MM-DD")
    args = parser.parse_args()

    if args.id:
        asyncio.run(_replay_by_id(args.id))
    elif args.since:
        asyncio.run(_replay_since(args.since))
    else:
        parser.error("Either --id or --since is required")


if __name__ == "__main__":
    main()
