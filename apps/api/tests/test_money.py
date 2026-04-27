"""Money helpers — everything is BIGINT centimes."""

from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from jumlaos.shared.money import (
    MoneyError,
    apply_vat,
    centimes_to_dh,
    dh_to_centimes,
    format_mad,
)


class TestCentimesConversion:
    def test_round_trip_whole_dirham(self) -> None:
        assert dh_to_centimes(10) == 1000
        assert centimes_to_dh(1000) == Decimal("10.00")

    def test_rounds_half_up(self) -> None:
        assert dh_to_centimes("0.005") == 1  # half-up

    def test_rejects_negative(self) -> None:
        with pytest.raises(MoneyError):
            dh_to_centimes("-1.00")

    def test_rejects_non_numeric(self) -> None:
        with pytest.raises(MoneyError):
            dh_to_centimes("not-a-number")

    def test_rejects_overflow(self) -> None:
        with pytest.raises(MoneyError):
            dh_to_centimes("999999999999999999")


class TestApplyVat:
    def test_twenty_percent(self) -> None:
        vat, total = apply_vat(10_000, 2000)
        assert vat == 2_000
        assert total == 12_000

    def test_seven_percent_rounds_half_up(self) -> None:
        vat, total = apply_vat(1_000, 700)
        assert vat == 70
        assert total == 1_070

    def test_zero_vat(self) -> None:
        vat, total = apply_vat(5_000, 0)
        assert vat == 0
        assert total == 5_000

    def test_rejects_out_of_range(self) -> None:
        with pytest.raises(MoneyError):
            apply_vat(100, -1)
        with pytest.raises(MoneyError):
            apply_vat(100, 10_001)


class TestFormat:
    def test_arabic_format(self) -> None:
        s = format_mad(1_234_567, locale="ar-MA")
        assert "د.م." in s

    def test_french_format(self) -> None:
        s = format_mad(1_234_567, locale="fr-MA")
        assert "MAD" in s


@given(st.integers(min_value=0, max_value=10_000_000_000))
def test_centimes_roundtrip_property(c: int) -> None:
    # BIGINT centimes <-> Decimal MAD roundtrips losslessly at 2 decimals.
    assert dh_to_centimes(centimes_to_dh(c)) == c
