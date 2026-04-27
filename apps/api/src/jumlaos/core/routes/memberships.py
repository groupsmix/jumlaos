"""Membership management (invite / revoke). Owner + manager only."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jumlaos.core.context import RequestContext
from jumlaos.core.deps import current_context, db
from jumlaos.core.errors import Conflict, Forbidden, NotFound
from jumlaos.core.models import Membership, MembershipStatus, Role, User
from jumlaos.shared.phone import PhoneError, normalize_ma

router = APIRouter()


class InviteRequest(BaseModel):
    phone: str = Field(min_length=5, max_length=25)
    role: Role
    display_name: str | None = None


class MembershipOut(BaseModel):
    id: int
    user_id: int
    phone: str
    role: str
    status: str


def _require_admin(ctx: RequestContext) -> None:
    if ctx.role not in {Role.OWNER, Role.MANAGER}:
        raise Forbidden("only_owner_or_manager_can_manage_memberships")


@router.get("", response_model=list[MembershipOut])
async def list_memberships(
    ctx: RequestContext = Depends(current_context),
    session: AsyncSession = Depends(db),
) -> list[MembershipOut]:
    stmt = (
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(Membership.business_id == ctx.business_id)
        .order_by(Membership.created_at.asc())
    )
    rows = (await session.execute(stmt)).all()
    return [
        MembershipOut(
            id=m.id,
            user_id=u.id,
            phone=u.phone_e164,
            role=m.role.value,
            status=m.status.value,
        )
        for m, u in rows
    ]


@router.post("/invite", response_model=MembershipOut)
async def invite(
    body: InviteRequest,
    ctx: RequestContext = Depends(current_context),
    session: AsyncSession = Depends(db),
) -> MembershipOut:
    _require_admin(ctx)
    if body.role == Role.OWNER:
        raise Forbidden("cannot_invite_another_owner")
    try:
        phone = normalize_ma(body.phone)
    except PhoneError as exc:
        raise Conflict("invalid_phone") from exc

    user = (
        await session.execute(select(User).where(User.phone_e164 == phone))
    ).scalar_one_or_none()
    if user is None:
        user = User(phone_e164=phone, display_name=body.display_name)
        session.add(user)
        await session.flush()

    existing = (
        await session.execute(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.business_id == ctx.business_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        if existing.status == MembershipStatus.ACTIVE:
            raise Conflict("membership_already_active")
        existing.status = MembershipStatus.ACTIVE
        existing.role = body.role
        m = existing
    else:
        m = Membership(
            user_id=user.id,
            business_id=ctx.business_id,
            role=body.role,
            invited_by_user_id=ctx.user_id,
            status=MembershipStatus.ACTIVE,
        )
        session.add(m)
        await session.flush()

    return MembershipOut(
        id=m.id,
        user_id=user.id,
        phone=user.phone_e164,
        role=m.role.value,
        status=m.status.value,
    )


@router.patch("/{membership_id}", response_model=MembershipOut)
async def update_membership(
    membership_id: int,
    role: Role | None = None,
    revoke: bool = False,
    ctx: RequestContext = Depends(current_context),
    session: AsyncSession = Depends(db),
) -> MembershipOut:
    _require_admin(ctx)
    m = (
        await session.execute(
            select(Membership).where(
                Membership.id == membership_id,
                Membership.business_id == ctx.business_id,
            )
        )
    ).scalar_one_or_none()
    if m is None:
        raise NotFound("membership_not_found")
    if m.role == Role.OWNER:
        raise Forbidden("cannot_modify_owner_membership")

    if role is not None:
        if role == Role.OWNER:
            raise Forbidden("cannot_promote_to_owner")
        m.role = role
    if revoke:
        m.status = MembershipStatus.REVOKED

    user = (await session.execute(select(User).where(User.id == m.user_id))).scalar_one()

    return MembershipOut(
        id=m.id,
        user_id=user.id,
        phone=user.phone_e164,
        role=m.role.value,
        status=m.status.value,
    )
