"""Domain event bus.

`publish` writes to `domain_events` in the same transaction as the state
change. A Procrastinate worker fans events out to subscribers (see
`jumlaos.workers`).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from jumlaos.core.models import DomainEvent


async def publish(
    session: AsyncSession,
    *,
    business_id: int,
    kind: str,
    payload: dict[str, Any],
    version: int = 1,
) -> DomainEvent:
    """Append a domain event. Commit is the caller's responsibility."""
    evt = DomainEvent(
        business_id=business_id,
        kind=kind,
        payload=payload,
        version=version,
    )
    session.add(evt)
    await session.flush()
    return evt
