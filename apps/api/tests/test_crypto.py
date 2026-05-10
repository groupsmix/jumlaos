"""F29: Fernet field encryption tests."""

from __future__ import annotations

from jumlaos.shared.adapters.crypto import decrypt_field, encrypt_field


class TestFieldEncryption:
    def test_roundtrip(self) -> None:
        plain = "123456789012345"
        encrypted = encrypt_field(plain)
        assert encrypted is not None
        assert encrypted != plain
        assert decrypt_field(encrypted) == plain

    def test_none_passthrough(self) -> None:
        assert encrypt_field(None) is None
        assert decrypt_field(None) is None

    def test_different_inputs_different_ciphertexts(self) -> None:
        a = encrypt_field("AAA")
        b = encrypt_field("BBB")
        assert a != b

    def test_same_input_different_ciphertexts(self) -> None:
        """Fernet uses random IVs, so same plaintext produces different ciphertext."""
        a = encrypt_field("same")
        b = encrypt_field("same")
        assert a != b
        assert decrypt_field(a) == decrypt_field(b) == "same"

    def test_corrupt_ciphertext_returns_error_prefix(self) -> None:
        result = decrypt_field("not-valid-fernet-token")
        assert result is not None
        assert result.startswith("[DECRYPT_ERROR]")

    def test_arabic_text(self) -> None:
        """Tax IDs may contain Arabic numerals or text."""
        plain = "رقم الضريبة 12345"
        encrypted = encrypt_field(plain)
        assert decrypt_field(encrypted) == plain

    def test_empty_string(self) -> None:
        encrypted = encrypt_field("")
        assert decrypt_field(encrypted) == ""
