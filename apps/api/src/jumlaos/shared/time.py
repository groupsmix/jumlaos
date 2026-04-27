"""Time helpers. Everything is TIMESTAMPTZ, all times in UTC internally."""

from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("naive datetime is not allowed; use utcnow()")
    return dt.astimezone(UTC)
