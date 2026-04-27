"""Audit log helper. Call from handlers whenever state changes."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from jumlaos.core.models import AuditLog


async def record(
    session: AsyncSession,
    *,
    business_id: int | None,
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> None:
    session.add(
        AuditLog(
            business_id=business_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before=before,
            after=after,
            request_id=request_id,
        )
    )
