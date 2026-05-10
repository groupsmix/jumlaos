"""F29: Application-side AEAD encryption for sensitive fields (tax IDs).

Uses Fernet (AES-128-CBC + HMAC-SHA256) keyed by a deterministic derivation
of the app secret. In prod, the secret key should come from a KMS-backed
env var so it can be rotated without redeployment.

Fields encrypted: ice_number, rc_number, if_number, cnss_number,
dgi_taxpayer_id on Business and Debtor models.

Usage::

    from jumlaos.shared.adapters.crypto import encrypt_field, decrypt_field

    encrypted = encrypt_field("123456789012345")
    plain = decrypt_field(encrypted)
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from jumlaos.config import get_settings


def _derive_key() -> bytes:
    """Derive a 32-byte Fernet key from the app secret via SHA-256.

    Fernet requires a URL-safe base64-encoded 32-byte key. We derive it
    deterministically from the secret_key so there is no extra env var
    to manage in dev. In prod, consider a dedicated ``FIELD_ENCRYPTION_KEY``
    env var backed by a KMS.
    """
    raw = hashlib.sha256(get_settings().secret_key.encode()).digest()
    return base64.urlsafe_b64encode(raw)


def encrypt_field(plaintext: str | None) -> str | None:
    """Encrypt a plaintext string. Returns None if input is None."""
    if plaintext is None:
        return None
    f = Fernet(_derive_key())
    return f.encrypt(plaintext.encode()).decode("ascii")


def decrypt_field(ciphertext: str | None) -> str | None:
    """Decrypt a ciphertext string. Returns None if input is None.

    Returns the original ciphertext prefixed with ``[DECRYPT_ERROR]`` on
    failure so callers never silently swallow corruption.
    """
    if ciphertext is None:
        return None
    f = Fernet(_derive_key())
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except (InvalidToken, Exception):
        return f"[DECRYPT_ERROR]{ciphertext[:20]}"
