"""Auth: phone OTP request + verify + logout + switch-business."""

# NOTE: ``from __future__ import annotations`` is intentionally omitted here.
# slowapi wraps the route handlers via ``functools.wraps``, and FastAPI uses
# ``typing.get_type_hints`` on the wrapped function. With future-annotations
# enabled, the body schemas (``OtpRequest``, ``OtpVerify``) come through as
# ``ForwardRef("OtpRequest")`` which the wrapper's globals can't resolve at
# OpenAPI build time. Keeping concrete typing here keeps slowapi + FastAPI
# happy without sprinkling Annotated[...] everywhere.

import uuid
from datetime import timedelta

from fastapi import APIRouter, Body, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from jumlaos.config import get_settings
from jumlaos.core.audit import record as audit_record
from jumlaos.core.context import RequestContext
from jumlaos.core.deps import ACCESS_COOKIE, REFRESH_COOKIE, current_context, db
from jumlaos.core.errors import Conflict, NotFound, Unauthorized
from jumlaos.core.models import Membership, MembershipStatus, OtpCode, RefreshToken, Role, User
from jumlaos.core.rate_limit import ip_key, limiter, phone_key, user_key
from jumlaos.core.security import (
    decode_token,
    generate_otp,
    hash_code,
    issue_access_token,
    issue_refresh_token,
    verify_code,
)
from jumlaos.logging import get_logger
from jumlaos.shared.otp_transport import deliver_otp
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
    # F09: SameSite=Strict on the access cookie defends against CSRF-by-cookie
    # for cross-site top-level navigations. Refresh stays Lax because some
    # browsers drop Strict cookies on first-party redirects after login.
    response.set_cookie(
        ACCESS_COOKIE,
        access,
        httponly=True,
        secure=secure,
        samesite="strict",
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


def _next_lockout_window(consecutive_failures: int) -> timedelta:
    """F08 exponential backoff: 15 min → 1 h → 24 h."""
    if consecutive_failures < 5:
        return timedelta(0)
    if consecutive_failures < 10:
        return timedelta(minutes=15)
    if consecutive_failures < 20:
        return timedelta(hours=1)
    return timedelta(hours=24)


@router.post("/otp/request", response_model=OtpRequestResponse)
@limiter.limit("1/minute", key_func=phone_key)
@limiter.limit("5/minute", key_func=ip_key)
async def otp_request(
    request: Request,
    body: OtpRequest = Body(...),
    session: AsyncSession = Depends(db),
) -> OtpRequestResponse:
    settings = get_settings()
    try:
        phone = normalize_ma(body.phone)
    except PhoneError as exc:
        raise Unauthorized("invalid_phone") from exc

    now = utcnow()

    # F08 — refuse to issue an OTP while the *user* is locked out. Per-phone
    # and per-IP rate limits are enforced by slowapi above (F10/F20).
    locked_user = (
        await session.execute(
            select(User).where(User.phone_e164 == phone, User.otp_lockout_until > now)
        )
    ).scalar_one_or_none()
    if locked_user is not None:
        from jumlaos.core.errors import RateLimited

        raise RateLimited("otp_phone_locked")

    code = generate_otp(dev_override="000000" if settings.is_dev else None)

    session.add(
        OtpCode(
            phone_e164=phone,
            code_hash=hash_code(code),
            expires_at=utcnow() + timedelta(seconds=settings.otp_ttl_seconds),
            ip=request.client.host if request.client else None,
        )
    )
    if settings.is_dev:
        log.info("dev_otp_generated", phone=phone, code=code)
    # F07 — dispatch out of band so the route never blocks on Meta's API.
    await deliver_otp(phone_e164=phone, code=code)

    return OtpRequestResponse(
        phone=phone,
        expires_in=settings.otp_ttl_seconds,
    )


@router.post("/otp/verify", response_model=OtpVerifyResponse)
@limiter.limit("5/minute", key_func=phone_key)
@limiter.limit("30/minute", key_func=ip_key)
async def otp_verify(
    request: Request,
    response: Response,
    body: OtpVerify = Body(...),
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

        from jumlaos.core.db import get_sessionmaker

        # F18 — increment attempts, lock the phone, AND write the audit record
        # in a single isolated session. The request session rolls back on the
        # Unauthorized raise below; using the same isolated session for all
        # three writes ensures nothing is lost.
        new_attempts = otp.attempts + 1
        async with get_sessionmaker()() as attempt_session:
            await attempt_session.execute(
                text("UPDATE otp_codes SET attempts = attempts + 1 WHERE id = :id"),
                {"id": otp.id},
            )

            # F08 — if the user has hit otp_max_attempts on this code, lock the
            # *phone* (not just this code row). Exponential backoff escalates
            # with consecutive failed attempt windows.
            if new_attempts >= settings.otp_max_attempts:
                window = _next_lockout_window(new_attempts)
                if window > timedelta(0):
                    await attempt_session.execute(
                        text(
                            "UPDATE users SET otp_lockout_until = :until WHERE phone_e164 = :phone"
                        ),
                        {"until": now + window, "phone": phone},
                    )

            # Write the audit record on the same isolated session so it
            # survives the Unauthorized rollback on the request session.
            await audit_record(
                attempt_session,
                business_id=None,
                user_id=None,
                action="auth.otp.verify_failed",
                entity_type="auth",
                after={"phone": phone, "reason": "mismatch", "attempts": new_attempts},
                request=request,
            )
            await attempt_session.commit()

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
    family_id = uuid.uuid4().hex
    session.add(RefreshToken(user_id=user.id, jti=jti, family_id=family_id))
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
        except Unauthorized:  # noqa: S110 — best-effort revocation on logout
            pass

    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")
    return {"status": "ok"}


@router.post("/refresh")
@limiter.limit("6/minute", key_func=user_key)
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
    if rt is None:
        raise Unauthorized("refresh_token_revoked_or_invalid")

    # F19 — reuse detection. A presented jti that is already revoked means the
    # original holder rotated, then the *old* token came back later (only
    # possible if it was leaked). Revoke the entire family and audit.
    if rt.revoked_at is not None:
        await session.execute(
            text(
                """
                UPDATE refresh_tokens
                SET revoked_at = COALESCE(revoked_at, now()),
                    revoked_reason = 'reuse_detected'
                WHERE family_id = :fid
                """
            ),
            {"fid": rt.family_id},
        )
        await audit_record(
            session,
            business_id=None,
            user_id=user_id,
            action="auth.refresh.reuse_detected",
            entity_type="auth",
            after={"family_id": rt.family_id, "jti": jti},
            request=request,
        )
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

    # Rotate within the same family so we can detect reuse later.
    rt.revoked_at = utcnow()
    rt.revoked_reason = "rotated"
    session.add(RefreshToken(user_id=user_id, jti=new_jti, family_id=rt.family_id))

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
    family_id = uuid.uuid4().hex
    session.add(RefreshToken(user_id=ctx.user_id, jti=jti, family_id=family_id))
    _set_auth_cookies(response, access=access, refresh=refresh)
    return {"business_id": m.business_id, "role": m.role.value}
