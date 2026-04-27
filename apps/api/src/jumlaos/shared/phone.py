"""Moroccan phone number normalization.

Accepts the 5 common formats a Moroccan jumala will enter and returns a
canonical E.164 string (`+212XXXXXXXXX`). Everything in the DB is E.164.
"""

from __future__ import annotations

import phonenumbers
from phonenumbers import NumberParseException


class PhoneError(ValueError):
    """Raised for invalid phone numbers."""


def normalize_ma(raw: str) -> str:
    """Normalize any Moroccan-looking number to E.164.

    Examples accepted:
        06 12 34 56 78     ->  +212612345678
        +212 6 12 34 56 78 ->  +212612345678
        00212 6 12345678   ->  +212612345678
        212612345678       ->  +212612345678
        6 12 34 56 78      ->  +212612345678
    """
    if not raw or not isinstance(raw, str):
        raise PhoneError("phone is required")
    cleaned = raw.strip()
    try:
        parsed = phonenumbers.parse(cleaned, "MA")
    except NumberParseException as exc:
        raise PhoneError(f"invalid phone: {raw!r}") from exc
    if not phonenumbers.is_valid_number(parsed):
        raise PhoneError(f"invalid phone: {raw!r}")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def is_moroccan_mobile(e164: str) -> bool:
    """Return True if the E.164 number is a Moroccan mobile (06/07)."""
    if not e164.startswith("+212"):
        return False
    digits = e164.removeprefix("+212")
    return len(digits) == 9 and digits[0] in {"6", "7"}
