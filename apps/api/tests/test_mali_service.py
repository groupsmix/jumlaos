"""Pure-Python bits of mali.service."""

from __future__ import annotations

from datetime import date

from jumlaos.mali.service import _bucket_for, _normalize_alias


class TestAgingBuckets:
    def test_no_due(self) -> None:
        assert _bucket_for(date(2026, 5, 1), None) == "current"

    def test_future_due(self) -> None:
        assert _bucket_for(date(2026, 5, 1), date(2026, 6, 1)) == "current"

    def test_today(self) -> None:
        assert _bucket_for(date(2026, 5, 1), date(2026, 5, 1)) == "current"

    def test_bucket_1_30(self) -> None:
        assert _bucket_for(date(2026, 5, 1), date(2026, 4, 15)) == "1_30"

    def test_bucket_31_60(self) -> None:
        assert _bucket_for(date(2026, 5, 1), date(2026, 3, 10)) == "31_60"

    def test_bucket_61_90(self) -> None:
        assert _bucket_for(date(2026, 5, 1), date(2026, 2, 10)) == "61_90"

    def test_bucket_90_plus(self) -> None:
        assert _bucket_for(date(2026, 5, 1), date(2025, 11, 1)) == "90_plus"


class TestAliasNormalize:
    def test_lowercase_trim(self) -> None:
        assert _normalize_alias("  Ahmed Tahiri ") == "ahmed tahiri"

    def test_collapse_whitespace(self) -> None:
        assert _normalize_alias("Fatima   Zahra") == "fatima zahra"
