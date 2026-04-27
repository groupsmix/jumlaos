"""Audit log helper. Call from handlers whenever state changes."""

from __future__ import annotations

from typing import Any
from fastapi import Request

from sqlalchemy.ext.asyncio import AsyncSession

from jumlaos.core.db import get_sessionmaker
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
    request: Request | None = None,
) -> None:
    ip = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    
    # Use a separate session to ensure the audit log is committed even if the main transaction rolls back
    async with get_sessionmaker()() as audit_session:
        audit_session.add(
            AuditLog(
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
        await audit_session.commit()
