"""OTP hashing + JWT access & refresh tokens.

OTP codes are short-lived (10 min) and low-entropy (6 digits) — we hash them
with HMAC-SHA256 keyed by the app secret. Constant-time comparison at
verify. No bcrypt / argon2 needed for this use case.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from jumlaos.config import get_settings
from jumlaos.core.errors import Unauthorized
from jumlaos.shared.time import utcnow

ALGORITHM = "HS256"


def hash_code(code: str) -> str:
    secret = get_settings().secret_key.encode()
    return hmac.new(secret, code.encode(), hashlib.sha256).hexdigest()


def verify_code(code: str, hashed: str) -> bool:
    return hmac.compare_digest(hash_code(code), hashed)


def generate_otp(*, dev_override: str | None = None) -> str:
    """Return a 6-digit OTP. In dev, returns '000000' unconditionally."""
    if dev_override is not None:
        return dev_override
    # secrets.randbelow is cryptographically secure
    return f"{secrets.randbelow(1_000_000):06d}"


def issue_access_token(*, user_id: int, business_id: int | None, role: str | None) -> str:
    settings = get_settings()
    now = utcnow()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "bid": business_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.access_token_ttl_seconds)).timestamp()),
        "typ": "access",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def issue_refresh_token(*, user_id: int) -> str:
    settings = get_settings()
    now = utcnow()
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.refresh_token_ttl_seconds)).timestamp()),
        "typ": "refresh",
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str, *, expected_type: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise Unauthorized("invalid_token") from exc
    if payload.get("typ") != expected_type:
        raise Unauthorized("wrong_token_type")
    return payload


def token_expired(payload: dict[str, Any]) -> bool:
    exp = payload.get("exp")
    if exp is None:
        return True
    return datetime.fromtimestamp(exp).astimezone(utcnow().tzinfo) < utcnow()
