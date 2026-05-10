"""F33: log-redaction policy tests.

Verify that phone numbers and IPs are hashed before reaching the log
renderer, and that the hash is consistent (same input => same output).
"""

from __future__ import annotations

from jumlaos.logging import _hmac_hash, _redact_value, redact_pii


class TestRedactValue:
    def test_phone_e164_is_redacted(self) -> None:
        result = _redact_value("+212600000001")
        assert isinstance(result, str)
        assert result.startswith("phone:")
        assert "+212" not in result

    def test_ipv4_is_redacted(self) -> None:
        result = _redact_value("192.168.1.1")
        assert isinstance(result, str)
        assert result.startswith("ip:")
        assert "192" not in result

    def test_non_pii_string_passes_through(self) -> None:
        assert _redact_value("hello world") == "hello world"

    def test_non_string_passes_through(self) -> None:
        assert _redact_value(42) == 42
        assert _redact_value(None) is None


class TestHmacHash:
    def test_consistent_output(self) -> None:
        assert _hmac_hash("+212600000001") == _hmac_hash("+212600000001")

    def test_different_inputs_differ(self) -> None:
        assert _hmac_hash("+212600000001") != _hmac_hash("+212600000002")

    def test_output_is_hex(self) -> None:
        h = _hmac_hash("test")
        assert len(h) == 16
        int(h, 16)  # must not raise


class TestRedactPiiProcessor:
    def test_phone_key_redacted(self) -> None:
        event_dict = {"phone": "+212600000001", "action": "otp.request"}
        result = redact_pii(None, "info", event_dict)
        assert result["phone"].startswith("phone:")
        assert result["action"] == "otp.request"

    def test_ip_key_redacted(self) -> None:
        event_dict = {"ip": "10.0.0.1", "action": "auth.login"}
        result = redact_pii(None, "info", event_dict)
        assert result["ip"].startswith("ip:")

    def test_non_redact_keys_untouched(self) -> None:
        event_dict = {"user_id": 42, "action": "test"}
        result = redact_pii(None, "info", event_dict)
        assert result == {"user_id": 42, "action": "test"}
