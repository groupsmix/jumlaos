"""FastAPI dependencies: auth, tenancy, RBAC."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Cookie, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jumlaos.core.context import RequestContext
from jumlaos.core.db import get_session
from jumlaos.core.errors import Forbidden, Unauthorized
from jumlaos.core.models import Membership, MembershipStatus, Role
from jumlaos.core.security import decode_token

ACCESS_COOKIE = "jumlaos_access"
REFRESH_COOKIE = "jumlaos_refresh"


async def db() -> AsyncIterator[AsyncSession]:
    async for session in get_session():
        yield session


async def current_context(
    access_cookie: str | None = Cookie(default=None, alias=ACCESS_COOKIE),
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(db),
) -> RequestContext:
    """Resolve the current user + business from the JWT. Verifies membership."""
    token = access_cookie
    if token is None and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise Unauthorized("missing_credentials")
    payload = decode_token(token, expected_type="access")

    user_id_raw = payload.get("sub")
    business_id = payload.get("bid")
    role_raw = payload.get("role")
    if user_id_raw is None or business_id is None or role_raw is None:
        raise Unauthorized("incomplete_token")

    user_id = int(user_id_raw)
    role = Role(role_raw)

    # Re-verify active membership (revocations must take effect on next request).
    stmt = select(Membership).where(
        Membership.user_id == user_id,
        Membership.business_id == business_id,
        Membership.status == MembershipStatus.ACTIVE,
    )
    if (await session.execute(stmt)).scalar_one_or_none() is None:
        raise Forbidden("membership_revoked_or_missing")

    return RequestContext(user_id=user_id, business_id=int(business_id), role=role)


def require_role(*roles: Role):  # type: ignore[no-untyped-def]
    """Return a dependency that asserts the caller has one of the roles."""

    async def _check(ctx: RequestContext = Depends(current_context)) -> RequestContext:
        ctx.require(*roles)
        return ctx

    return _check
