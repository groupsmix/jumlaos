"""Smoke test: prod boot with insecure defaults must fail.

The audit calls this out as a quick win: today the app boots silently with
insecure defaults if only JUMLAOS_SECRET_KEY is set. These tests assert that
prod mode rejects every insecure default at boot time.

Uses monkeypatch to set env vars directly because pydantic-settings reads
validation_alias env vars and init kwargs interact non-trivially.
"""

from __future__ import annotations

import pytest

from jumlaos.config import Settings


def _set_valid_prod_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set all env vars needed for a valid prod boot."""
    monkeypatch.setenv("JUMLAOS_ENV", "prod")
    monkeypatch.setenv(
        "JUMLAOS_SECRET_KEY",
        "a-real-prod-secret-key-that-is-at-least-32-chars-long",
    )
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://real:real@db.internal:5432/jumlaos",
    )
    monkeypatch.setenv(
        "DATABASE_URL_SYNC",
        "postgresql://real:real@db.internal:5432/jumlaos?sslmode=verify-full",
    )
    monkeypatch.setenv("REDIS_URL", "redis://redis.internal:6379/0")
    monkeypatch.setenv("JUMLAOS_ALLOWED_ORIGINS", "https://app.jumlaos.ma")
    monkeypatch.setenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "prod-verify-token")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "prod-app-secret")
    monkeypatch.setenv("OTP_TRANSPORT", "whatsapp")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "1234")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "tok")
    monkeypatch.setenv("R2_ENDPOINT", "https://r2.example.com")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("R2_BUCKET", "jumlaos-prod")


class TestProdBootSecurity:
    def test_valid_prod_boots(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_valid_prod_env(monkeypatch)
        s = Settings()
        assert s.is_prod

    def test_prod_rejects_default_database_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_valid_prod_env(monkeypatch)
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql+asyncpg://jumlaos:jumlaos@localhost:5432/jumlaos",
        )
        with pytest.raises(ValueError, match="DATABASE_URL"):
            Settings()

    def test_prod_rejects_default_redis_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_valid_prod_env(monkeypatch)
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        with pytest.raises(ValueError, match="REDIS_URL"):
            Settings()

    def test_prod_rejects_default_origins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_valid_prod_env(monkeypatch)
        monkeypatch.setenv("JUMLAOS_ALLOWED_ORIGINS", "http://localhost:3000")
        with pytest.raises(ValueError, match="ALLOWED_ORIGINS"):
            Settings()

    def test_prod_rejects_log_otp_transport(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_valid_prod_env(monkeypatch)
        monkeypatch.setenv("OTP_TRANSPORT", "log")
        with pytest.raises(ValueError, match="OTP_TRANSPORT"):
            Settings()

    def test_prod_rejects_missing_sslmode_in_sync_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """F22: database_url_sync must include sslmode= in prod."""
        _set_valid_prod_env(monkeypatch)
        monkeypatch.setenv(
            "DATABASE_URL_SYNC",
            "postgresql://real:real@db.internal:5432/jumlaos",
        )
        with pytest.raises(ValueError, match="sslmode"):
            Settings()

    def test_prod_rejects_default_r2_bucket(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_valid_prod_env(monkeypatch)
        monkeypatch.setenv("R2_BUCKET", "jumlaos-dev")
        with pytest.raises(ValueError, match="R2_BUCKET"):
            Settings()

    def test_dev_boots_fine_with_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Dev mode should boot with all defaults (no prod validation)."""
        monkeypatch.setenv("JUMLAOS_ENV", "dev")
        s = Settings()
        assert s.is_dev
