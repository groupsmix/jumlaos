"""JWT + OTP helpers."""

from __future__ import annotations

import pytest

from jumlaos.core.errors import Unauthorized
from jumlaos.core.security import (
    decode_token,
    generate_otp,
    hash_code,
    issue_access_token,
    issue_refresh_token,
    verify_code,
)


class TestOtp:
    def test_dev_override(self) -> None:
        assert generate_otp(dev_override="000000") == "000000"

    def test_six_digits(self) -> None:
        code = generate_otp()
        assert len(code) == 6
        assert code.isdigit()

    def test_hash_verify_roundtrip(self) -> None:
        h = hash_code("123456")
        assert verify_code("123456", h) is True
        assert verify_code("000000", h) is False


class TestJwt:
    def test_access_token_roundtrip(self) -> None:
        token = issue_access_token(user_id=7, business_id=3, role="owner")
        payload = decode_token(token, expected_type="access")
        assert payload["sub"] == "7"
        assert payload["bid"] == 3
        assert payload["role"] == "owner"

    def test_refresh_token_roundtrip(self) -> None:
        token = issue_refresh_token(user_id=9)
        payload = decode_token(token, expected_type="refresh")
        assert payload["sub"] == "9"
        assert payload["typ"] == "refresh"

    def test_wrong_type_rejected(self) -> None:
        refresh = issue_refresh_token(user_id=1)
        with pytest.raises(Unauthorized):
            decode_token(refresh, expected_type="access")

    def test_tampered_rejected(self) -> None:
        token = issue_access_token(user_id=1, business_id=1, role="owner")
        bad = token[:-2] + ("AA" if not token.endswith("AA") else "BB")
        with pytest.raises(Unauthorized):
            decode_token(bad, expected_type="access")
