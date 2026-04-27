"""/v1/me and /v1/businesses/current."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jumlaos.core.context import RequestContext
from jumlaos.core.deps import current_context, db
from jumlaos.core.errors import NotFound
from jumlaos.core.models import Business, Membership, MembershipStatus, User

router = APIRouter()


class MeResponse(BaseModel):
    id: int
    phone: str
    display_name: str | None
    locale: str
    current_business_id: int
    role: str
    permissions: dict[str, object]
    memberships: list[dict[str, object]]


class BusinessResponse(BaseModel):
    id: int
    legal_name: str
    display_name: str
    phone: str
    city: str | None
    region: str | None
    plan: str
    modules_enabled: dict[str, object]


@router.get("/me", response_model=MeResponse)
async def me(
    ctx: RequestContext = Depends(current_context),
    session: AsyncSession = Depends(db),
) -> MeResponse:
    user = (await session.execute(select(User).where(User.id == ctx.user_id))).scalar_one_or_none()
    if user is None:
        raise NotFound("user_not_found")
    memberships = (
        (
            await session.execute(
                select(Membership).where(
                    Membership.user_id == ctx.user_id,
                    Membership.status == MembershipStatus.ACTIVE,
                )
            )
        )
        .scalars()
        .all()
    )

    perms: dict[str, object] = {}
    for m in memberships:
        if m.business_id == ctx.business_id:
            perms = dict(m.permissions or {})
            break

    return MeResponse(
        id=user.id,
        phone=user.phone_e164,
        display_name=user.display_name,
        locale=user.locale,
        current_business_id=ctx.business_id,
        role=ctx.role.value,
        permissions=perms,
        memberships=[{"business_id": m.business_id, "role": m.role.value} for m in memberships],
    )


@router.get("/businesses/current", response_model=BusinessResponse)
async def current_business(
    ctx: RequestContext = Depends(current_context),
    session: AsyncSession = Depends(db),
) -> BusinessResponse:
    biz = (
        await session.execute(select(Business).where(Business.id == ctx.business_id))
    ).scalar_one_or_none()
    if biz is None:
        raise NotFound("business_not_found")
    return BusinessResponse(
        id=biz.id,
        legal_name=biz.legal_name,
        display_name=biz.display_name,
        phone=biz.phone_e164,
        city=biz.city,
        region=biz.region,
        plan=biz.plan.value,
        modules_enabled=dict(biz.modules_enabled or {}),
    )
