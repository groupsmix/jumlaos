"""Moroccan phone normalization."""

from __future__ import annotations

import pytest

from jumlaos.shared.phone import PhoneError, is_moroccan_mobile, normalize_ma


@pytest.mark.parametrize(
    "raw",
    [
        "0612345678",
        "06 12 34 56 78",
        "+212612345678",
        "+212 6 12 34 56 78",
        "00212612345678",
        "212612345678",
    ],
)
def test_normalize_variants(raw: str) -> None:
    assert normalize_ma(raw) == "+212612345678"


@pytest.mark.parametrize("raw", ["", "   ", "abc", "+49", "012345"])
def test_rejects_invalid(raw: str) -> None:
    with pytest.raises(PhoneError):
        normalize_ma(raw)


def test_is_moroccan_mobile() -> None:
    assert is_moroccan_mobile("+212612345678") is True
    assert is_moroccan_mobile("+212712345678") is True
    assert is_moroccan_mobile("+212522222222") is False
    assert is_moroccan_mobile("+33612345678") is False
