"""Central settings. Reads from env, validates via pydantic."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. All env vars prefixed `JUMLAOS_` unless noted."""

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    env: Literal["dev", "test", "staging", "prod"] = Field(
        default="dev", validation_alias="JUMLAOS_ENV"
    )
    log_level: str = Field(default="INFO", validation_alias="JUMLAOS_LOG_LEVEL")
    secret_key: str = Field(
        default="dev-secret-key-change-me-in-prod-must-be-32-chars-or-more",
        validation_alias="JUMLAOS_SECRET_KEY",
    )
    allowed_origins: str = Field(
        default="http://localhost:3000",
        validation_alias="JUMLAOS_ALLOWED_ORIGINS",
    )

    database_url: str = Field(
        default="postgresql+asyncpg://jumlaos:jumlaos@localhost:5432/jumlaos",
        validation_alias="DATABASE_URL",
    )
    database_url_sync: str = Field(
        default="postgresql://jumlaos:jumlaos@localhost:5432/jumlaos",
        validation_alias="DATABASE_URL_SYNC",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")

    # Auth
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 60 * 60 * 24 * 30
    otp_ttl_seconds: int = 600
    otp_max_attempts: int = 5
    otp_lockout_seconds: int = 900

    # WhatsApp Cloud API
    whatsapp_phone_number_id: str = Field(default="", validation_alias="WHATSAPP_PHONE_NUMBER_ID")
    whatsapp_access_token: str = Field(default="", validation_alias="WHATSAPP_ACCESS_TOKEN")
    whatsapp_webhook_verify_token: str = Field(
        default="dev-verify-token", validation_alias="WHATSAPP_WEBHOOK_VERIFY_TOKEN"
    )
    whatsapp_app_secret: str = Field(default="", validation_alias="WHATSAPP_APP_SECRET")

    # R2 (S3-compatible)
    r2_endpoint: str = Field(default="", validation_alias="R2_ENDPOINT")
    r2_access_key_id: str = Field(default="", validation_alias="R2_ACCESS_KEY_ID")
    r2_secret_access_key: str = Field(default="", validation_alias="R2_SECRET_ACCESS_KEY")
    r2_bucket: str = Field(default="jumlaos-dev", validation_alias="R2_BUCKET")

    # LLM / STT / OCR
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")

    # Observability
    sentry_dsn: str = Field(default="", validation_alias="SENTRY_DSN")

    @field_validator("secret_key")
    @classmethod
    def _validate_secret(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JUMLAOS_SECRET_KEY must be at least 32 characters")
        return value

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"

    @property
    def is_dev(self) -> bool:
        return self.env == "dev"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
