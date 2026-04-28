"""Central settings. Reads from env, validates via pydantic."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
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
    database_pool_size: int = Field(default=20, validation_alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, validation_alias="DATABASE_MAX_OVERFLOW")
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")

    # Auth
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 60 * 60 * 24 * 30
    otp_ttl_seconds: int = 600
    otp_max_attempts: int = 5
    otp_lockout_seconds: int = 900
    otp_transport: Literal["whatsapp", "sms", "log"] = Field(
        default="log", validation_alias="OTP_TRANSPORT"
    )

    # Request limits
    max_request_bytes: int = Field(default=256 * 1024, validation_alias="JUMLAOS_MAX_REQUEST_BYTES")
    max_webhook_bytes: int = Field(
        default=16 * 1024 * 1024, validation_alias="JUMLAOS_MAX_WEBHOOK_BYTES"
    )

    # SMS fallback (Twilio-compatible). Empty => SMS transport disabled.
    sms_provider: Literal["twilio", "none"] = Field(default="none", validation_alias="SMS_PROVIDER")
    sms_account_sid: str = Field(default="", validation_alias="SMS_ACCOUNT_SID")
    sms_auth_token: str = Field(default="", validation_alias="SMS_AUTH_TOKEN")
    sms_from_number: str = Field(default="", validation_alias="SMS_FROM_NUMBER")

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

    @model_validator(mode="after")
    def _validate_prod_security(self) -> Settings:
        if os.getenv("FLY_APP_NAME") and self.env == "dev":
            raise ValueError("Cannot run in dev mode on Fly.io. Set JUMLAOS_ENV=prod or staging.")
        if self.env in ("prod", "staging"):
            if self.secret_key == "dev-secret-key-change-me-in-prod-must-be-32-chars-or-more":
                raise ValueError("Must provide secure JUMLAOS_SECRET_KEY in prod/staging")
            if self.whatsapp_webhook_verify_token == "dev-verify-token":
                raise ValueError(
                    "Must provide secure WHATSAPP_WEBHOOK_VERIFY_TOKEN in prod/staging"
                )
            if not self.whatsapp_app_secret:
                raise ValueError("Must provide secure WHATSAPP_APP_SECRET in prod/staging")
            # F21: refuse to boot prod with default infra/origin values.
            if self.database_url == "postgresql+asyncpg://jumlaos:jumlaos@localhost:5432/jumlaos":
                raise ValueError("Must provide secure DATABASE_URL in prod/staging")
            if self.database_url_sync == "postgresql://jumlaos:jumlaos@localhost:5432/jumlaos":
                raise ValueError("Must provide secure DATABASE_URL_SYNC in prod/staging")
            if "localhost" in self.redis_url or self.redis_url == "redis://localhost:6379/0":
                raise ValueError("Must provide non-localhost REDIS_URL in prod/staging")
            if self.allowed_origins == "http://localhost:3000":
                raise ValueError("Must provide secure JUMLAOS_ALLOWED_ORIGINS in prod/staging")
            if self.otp_transport == "log":
                raise ValueError("OTP_TRANSPORT=log is not allowed in prod/staging")
            if self.otp_transport == "sms" and self.sms_provider == "none":
                raise ValueError("OTP_TRANSPORT=sms requires a configured SMS_PROVIDER")
            if self.otp_transport == "whatsapp" and not (
                self.whatsapp_phone_number_id and self.whatsapp_access_token
            ):
                raise ValueError(
                    "OTP_TRANSPORT=whatsapp requires WHATSAPP_PHONE_NUMBER_ID + "
                    "WHATSAPP_ACCESS_TOKEN"
                )
        return self

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
