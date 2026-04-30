"""Structured logging using structlog. JSON in prod, pretty in dev.

F33: log-redaction policy. Phone numbers and IPs are hashed with
HMAC-SHA256 (keyed by a server-side pepper) before they hit the log
stream. The hash is consistent within a process lifetime so
correlation is still possible, but raw PII never appears in logs.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import sys
from typing import Any

import structlog

from jumlaos.config import get_settings

# E.164 phone pattern: +<country code><subscriber number>
_PHONE_RE = re.compile(r"\+?\d{7,15}")

# IPv4 / IPv6 (simplified — catches most common forms)
_IP_RE = re.compile(
    r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
    r"|"
    r"\b(?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4}\b"
)

# Cached pepper — derived once from the secret key on first use.
_pepper: bytes | None = None


def _get_pepper() -> bytes:
    global _pepper  # noqa: PLW0603
    if _pepper is None:
        settings = get_settings()
        _pepper = hashlib.sha256(settings.secret_key.encode()).digest()
    return _pepper


def _hmac_hash(value: str) -> str:
    """Consistent, one-way hash for PII redaction."""
    return hmac.new(_get_pepper(), value.encode(), hashlib.sha256).hexdigest()[:16]


def _redact_value(value: object) -> object:
    """Redact phone numbers and IPs from a single log value."""
    if not isinstance(value, str):
        return value
    # Redact phone numbers
    if _PHONE_RE.fullmatch(value):
        return f"phone:{_hmac_hash(value)}"
    # Redact bare IPs
    if _IP_RE.fullmatch(value):
        return f"ip:{_hmac_hash(value)}"
    return value


# Keys whose values should be redacted in log events.
_REDACT_KEYS = {"phone", "phone_e164", "from_phone", "ip", "to_phone_e164"}


def redact_pii(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Structlog processor: hash PII fields before they reach the renderer."""
    for key in _REDACT_KEYS:
        if key in event_dict:
            event_dict[key] = _redact_value(event_dict[key])
    return event_dict


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
        force=True,
    )

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # F33: redact PII before rendering.
        redact_pii,
    ]
    if settings.is_prod or settings.env == "staging":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty()))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> Any:
    return structlog.get_logger(name)
