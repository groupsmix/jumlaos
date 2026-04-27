"""Money lives as BIGINT centimes. This module is the only conversion surface.

Rules:
- Storage / transport: integer centimes, always.
- Display: `format_mad(centimes, locale)`.
- Parsing user input: `parse_mad(value)` raises on ambiguous values.

We never use float arithmetic for money. `Decimal` is used at the boundary
for parsing, then immediately converted to `int`.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Final

CENTIMES_PER_DIRHAM: Final[int] = 100
MAX_AMOUNT_CENTIMES: Final[int] = 10_000_000_000_000  # 100 billion MAD


class MoneyError(ValueError):
    """Raised for invalid monetary values."""


def centimes_to_dh(centimes: int) -> Decimal:
    """Lossless conversion for display / API responses."""
    if not isinstance(centimes, int):  # pragma: no cover - defensive
        raise MoneyError(f"centimes must be int, got {type(centimes).__name__}")
    return (Decimal(centimes) / Decimal(CENTIMES_PER_DIRHAM)).quantize(Decimal("0.01"))


def dh_to_centimes(dh: Decimal | int | str) -> int:
    """Parse a MAD amount into integer centimes. Raises on ambiguity."""
    try:
        value = Decimal(str(dh))
    except (InvalidOperation, TypeError) as exc:
        raise MoneyError(f"cannot parse MAD amount: {dh!r}") from exc
    # Round half-up at 2 decimals — MAD is not defined below 0.01.
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    centimes = int(quantized * CENTIMES_PER_DIRHAM)
    if centimes < 0:
        raise MoneyError(f"negative money amount: {dh!r}")
    if centimes > MAX_AMOUNT_CENTIMES:
        raise MoneyError(f"amount overflows MAX_AMOUNT_CENTIMES: {dh!r}")
    return centimes


def format_mad(centimes: int, *, locale: str = "ar-MA") -> str:
    """Render an integer centimes amount for humans.

    We keep formatting minimal and local to this module to avoid pulling in
    a heavy i18n dependency server-side. The frontend does proper locale
    formatting via `Intl.NumberFormat`.
    """
    dh = centimes_to_dh(centimes)
    integer, _, fractional = f"{dh:.2f}".partition(".")
    # Thousands separator: Arabic locale uses U+066C, French uses NBSP.
    sep = "\u066c" if locale.startswith("ar") else "\u00a0"
    grouped = _group_thousands(integer, sep)
    decimal_sep = "," if locale.startswith(("ar", "fr")) else "."
    suffix = "\u00a0د.م." if locale.startswith("ar") else "\u00a0MAD"
    return f"{grouped}{decimal_sep}{fractional}{suffix}"


def _group_thousands(integer: str, sep: str) -> str:
    out = []
    for i, ch in enumerate(reversed(integer)):
        if i and i % 3 == 0:
            out.append(sep)
        out.append(ch)
    return "".join(reversed(out))


def apply_vat(subtotal_centimes: int, vat_rate_bps: int) -> tuple[int, int]:
    """Return (vat_centimes, total_centimes) for an amount + VAT in bps.

    bps = basis points; 2000 bps = 20%. Rounds half-up to the nearest centime.
    """
    if vat_rate_bps < 0 or vat_rate_bps > 10_000:
        raise MoneyError(f"vat_rate_bps out of range: {vat_rate_bps}")
    vat = (Decimal(subtotal_centimes) * Decimal(vat_rate_bps) / Decimal(10_000)).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    vat_centimes = int(vat)
    return vat_centimes, subtotal_centimes + vat_centimes
