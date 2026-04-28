"""Auth: phone OTP request + verify + logout + switch-business."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from jumlaos.config import get_settings
from jumlaos.core.audit import record as audit_record
from jumlaos.core.context import RequestContext
from jumlaos.core.deps import ACCESS_COOKIE, REFRESH_COOKIE, current_context, db
from jumlaos.core.errors import Conflict, NotFound, RateLimited, Unauthorized
from jumlaos.core.models import Membership, MembershipStatus, OtpCode, RefreshToken, Role, User
from jumlaos.core.security import (
    decode_token,
    generate_otp,
    hash_code,
    issue_access_token,
    issue_refresh_token,
    verify_code,
)
from jumlaos.logging import get_logger
from jumlaos.shared.phone import PhoneError, normalize_ma
from jumlaos.shared.time import utcnow

log = get_logger()

router = APIRouter()


class OtpRequest(BaseModel):
    phone: str = Field(min_length=5, max_length=25)


class OtpRequestResponse(BaseModel):
    phone: str
    expires_in: int


class OtpVerify(BaseModel):
    phone: str
    code: str = Field(min_length=4, max_length=10)


class OtpVerifyResponse(BaseModel):
    user_id: int
    business_id: int | None
    role: str | None
    memberships: list[dict[str, object]]


class SwitchBusinessRequest(BaseModel):
    business_id: int


def _set_auth_cookies(response: Response, *, access: str, refresh: str) -> None:
    settings = get_settings()
    secure = settings.env in {"prod", "staging"}
    response.set_cookie(
        ACCESS_COOKIE,
        access,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.access_token_ttl_seconds,
        path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.refresh_token_ttl_seconds,
        path="/",
    )


@router.post("/otp/request", response_model=OtpRequestResponse)
async def otp_request(
    body: OtpRequest,
    request: Request,
    session: AsyncSession = Depends(db),
) -> OtpRequestResponse:
    settings = get_settings()
    try:
        phone = normalize_ma(body.phone)
    except PhoneError as exc:
        raise Unauthorized("invalid_phone") from exc

    now = utcnow()
    window = now - timedelta(minutes=1)

    # 1. Per-phone rate limit: max 1 request per minute
    recent_phone_stmt = select(func.count(OtpCode.id)).where(
        OtpCode.phone_e164 == phone,
        OtpCode.created_at > window,
    )
    recent_phone_count = (await session.execute(recent_phone_stmt)).scalar_one()
    if recent_phone_count >= 1:
        raise RateLimited("too_many_requests_for_phone")

    # 2. Per-IP rate limit: max 5 requests per minute
    ip = request.client.host if request.client else None
    if ip:
        recent_ip_stmt = select(func.count(OtpCode.id)).where(
            OtpCode.ip == ip,
            OtpCode.created_at > window,
        )
        recent_ip_count = (await session.execute(recent_ip_stmt)).scalar_one()
        if recent_ip_count >= 5:
            raise RateLimited("too_many_requests_from_ip")

    code = generate_otp(dev_override="000000" if settings.is_dev else None)

    session.add(
        OtpCode(
            phone_e164=phone,
            code_hash=hash_code(code),
            expires_at=utcnow() + timedelta(seconds=settings.otp_ttl_seconds),
            ip=request.client.host if request.client else None,
        )
    )
    # TODO(whatsapp): enqueue a WhatsApp template message for prod.
    if settings.is_dev:
        log.info("dev_otp_generated", phone=phone, code=code)

    return OtpRequestResponse(
        phone=phone,
        expires_in=settings.otp_ttl_seconds,
    )


@router.post("/otp/verify", response_model=OtpVerifyResponse)
async def otp_verify(
    body: OtpVerify,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(db),
) -> OtpVerifyResponse:
    settings = get_settings()
    try:
        phone = normalize_ma(body.phone)
    except PhoneError as exc:
        raise Unauthorized("invalid_phone") from exc

    now = utcnow()
    stmt = (
        select(OtpCode)
        .where(
            OtpCode.phone_e164 == phone,
            OtpCode.consumed_at.is_(None),
            OtpCode.expires_at > now,
        )
        .order_by(OtpCode.id.desc())
        .limit(1)
    )
    otp = (await session.execute(stmt)).scalar_one_or_none()

    if otp is None:
        await audit_record(
            session,
            business_id=None,
            user_id=None,
            action="auth.otp.verify_failed",
            entity_type="auth",
            after={"phone": phone, "reason": "not_found_or_expired"},
            request=request,
        )
        raise Unauthorized("otp_not_found_or_expired")

    if otp.attempts >= settings.otp_max_attempts:
        await audit_record(
            session,
            business_id=None,
            user_id=None,
            action="auth.otp.verify_failed",
            entity_type="auth",
            after={"phone": phone, "reason": "locked"},
            request=request,
        )
        raise Unauthorized("otp_locked")

    if not verify_code(body.code, otp.code_hash):
        from sqlalchemy import text

        await session.execute(
            text("UPDATE otp_codes SET attempts = attempts + 1 WHERE id = :id"), {"id": otp.id}
        )
        await session.commit()
        await audit_record(
            session,
            business_id=None,
            user_id=None,
            action="auth.otp.verify_failed",
            entity_type="auth",
            after={"phone": phone, "reason": "mismatch", "attempts": otp.attempts + 1},
            request=request,
        )
        raise Unauthorized("otp_mismatch")

    otp.consumed_at = now

    # upsert user
    user = (
        await session.execute(select(User).where(User.phone_e164 == phone))
    ).scalar_one_or_none()
    if user is None:
        user = User(phone_e164=phone)
        session.add(user)
        await session.flush()
    user.last_login_at = now

    # pick default membership (most-recently-active)
    memberships = (
        (
            await session.execute(
                select(Membership)
                .where(
                    Membership.user_id == user.id,
                    Membership.status == MembershipStatus.ACTIVE,
                )
                .order_by(Membership.updated_at.desc())
            )
        )
        .scalars()
        .all()
    )

    business_id: int | None = None
    role: Role | None = None
    if memberships:
        business_id = memberships[0].business_id
        role = memberships[0].role

    access = issue_access_token(
        user_id=user.id,
        business_id=business_id,
        role=role.value if role else None,
    )
    refresh, jti = issue_refresh_token(user_id=user.id)
    session.add(RefreshToken(user_id=user.id, jti=jti))
    _set_auth_cookies(response, access=access, refresh=refresh)

    await audit_record(
        session,
        business_id=business_id,
        user_id=user.id,
        action="auth.login",
        entity_type="auth",
        request=request,
    )

    return OtpVerifyResponse(
        user_id=user.id,
        business_id=business_id,
        role=role.value if role else None,
        memberships=[{"business_id": m.business_id, "role": m.role.value} for m in memberships],
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(db),
) -> dict[str, str]:
    token = request.cookies.get(REFRESH_COOKIE)
    if token:
        try:
            payload = decode_token(token, expected_type="refresh")
            jti = payload.get("jti")
            if jti:
                rt = (
                    await session.execute(select(RefreshToken).where(RefreshToken.jti == jti))
                ).scalar_one_or_none()
                if rt:
                    rt.revoked_at = utcnow()
        except Unauthorized:
            pass

    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")
    return {"status": "ok"}


@router.post("/refresh")
async def refresh_tokens(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(db),
) -> dict[str, str]:
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise Unauthorized("missing_refresh")
    payload = decode_token(token, expected_type="refresh")
    user_id = int(payload["sub"])
    jti = payload["jti"]

    rt = (
        await session.execute(select(RefreshToken).where(RefreshToken.jti == jti))
    ).scalar_one_or_none()
    if not rt or rt.revoked_at is not None:
        raise Unauthorized("refresh_token_revoked_or_invalid")

    rt.last_used_at = utcnow()

    # re-resolve default membership
    m = (
        await session.execute(
            select(Membership)
            .where(
                Membership.user_id == user_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
            .order_by(Membership.updated_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    access = issue_access_token(
        user_id=user_id,
        business_id=m.business_id if m else None,
        role=m.role.value if m else None,
    )
    new_refresh, new_jti = issue_refresh_token(user_id=user_id)

    # Revoke old one, add new one
    rt.revoked_at = utcnow()
    session.add(RefreshToken(user_id=user_id, jti=new_jti))

    _set_auth_cookies(response, access=access, refresh=new_refresh)
    return {"status": "ok"}


@router.post("/switch-business")
async def switch_business(
    body: SwitchBusinessRequest,
    response: Response,
    session: AsyncSession = Depends(db),
    ctx: RequestContext = Depends(current_context),
) -> dict[str, object]:
    stmt = select(Membership).where(
        Membership.user_id == ctx.user_id,
        Membership.business_id == body.business_id,
        Membership.status == MembershipStatus.ACTIVE,
    )
    m = (await session.execute(stmt)).scalar_one_or_none()
    if m is None:
        raise NotFound("membership_not_found")
    if m.business_id == ctx.business_id:
        raise Conflict("already_active_business")

    access = issue_access_token(
        user_id=ctx.user_id,
        business_id=m.business_id,
        role=m.role.value,
    )
    refresh, jti = issue_refresh_token(user_id=ctx.user_id)
    session.add(RefreshToken(user_id=ctx.user_id, jti=jti))
    _set_auth_cookies(response, access=access, refresh=refresh)
    return {"business_id": m.business_id, "role": m.role.value}
