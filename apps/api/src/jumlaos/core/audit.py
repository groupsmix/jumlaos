"""Audit log helper. Call from handlers whenever state changes.

F03 — writes go to ``audit_outbox`` on the *caller's* session in the same
transaction as the business action. A Procrastinate task drains the outbox
into the canonical ``audit_log`` table. If the caller's transaction rolls
back, the outbox row rolls back with it; we never log work that did not
actually happen.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from jumlaos.core.models import AuditOutbox


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
    request: Request | None = None,
) -> None:
    ip = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None

    session.add(
        AuditOutbox(
            business_id=business_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before=before,
            after=after,
            request_id=request_id,
            ip=ip,
            user_agent=user_agent,
        )
    )
