"""Unit tests for P0 audit fixes (F07, F08).

These tests cover the pure-function and HTTP-adapter layers added in the
P0 audit fix PR. Database-dependent paths (idempotency middleware, refresh
token reuse detection, audit outbox) are exercised by the integration test
suite in CI's Postgres job.
"""

from __future__ import annotations

from datetime import timedelta

import httpx
import pytest
import respx

from jumlaos.config import get_settings
from jumlaos.core.routes.auth import _next_lockout_window
from jumlaos.shared.adapters.sms import SmsSendError, send_sms
from jumlaos.shared.adapters.whatsapp import WhatsAppSendError, send_template
from jumlaos.shared.otp_transport import deliver_otp

# ---------------------------------------------------------------------------
# F08 — exponential backoff
# ---------------------------------------------------------------------------


class TestLockoutBackoff:
    def test_no_lockout_below_threshold(self) -> None:
        for n in range(5):
            assert _next_lockout_window(n) == timedelta(0)

    def test_first_window_is_fifteen_minutes(self) -> None:
        assert _next_lockout_window(5) == timedelta(minutes=15)
        assert _next_lockout_window(9) == timedelta(minutes=15)

    def test_second_window_is_one_hour(self) -> None:
        assert _next_lockout_window(10) == timedelta(hours=1)
        assert _next_lockout_window(19) == timedelta(hours=1)

    def test_third_window_is_one_day(self) -> None:
        assert _next_lockout_window(20) == timedelta(hours=24)
        assert _next_lockout_window(100) == timedelta(hours=24)


# ---------------------------------------------------------------------------
# F07 — WhatsApp adapter
# ---------------------------------------------------------------------------


class TestWhatsAppAdapter:
    @pytest.mark.asyncio
    async def test_missing_credentials_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "")
        monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "")
        get_settings.cache_clear()

        with pytest.raises(WhatsAppSendError, match="whatsapp_credentials_missing"):
            await send_template(
                to_phone_e164="+212600000001",
                template_name="jumlaos_otp",
                language_code="ar_MA",
                body_params=["123456"],
            )

    @pytest.mark.asyncio
    async def test_strips_plus_and_posts_template(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "abc123")
        monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "token-xyz")
        get_settings.cache_clear()

        with respx.mock(base_url="https://graph.facebook.com") as mock:
            route = mock.post("/v20.0/abc123/messages").mock(
                return_value=httpx.Response(200, json={"messages": [{"id": "wamid.1"}]})
            )
            result = await send_template(
                to_phone_e164="+212600000001",
                template_name="jumlaos_otp",
                language_code="ar_MA",
                body_params=["123456"],
            )

        assert result == {"messages": [{"id": "wamid.1"}]}
        assert route.called
        # Body had the leading '+' stripped per Meta's expectation.
        sent = route.calls.last.request.read().decode()
        assert '"to":"212600000001"' in sent
        assert '"text":"123456"' in sent

    @pytest.mark.asyncio
    async def test_4xx_response_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "abc123")
        monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "token-xyz")
        get_settings.cache_clear()

        with respx.mock(base_url="https://graph.facebook.com") as mock:
            mock.post("/v20.0/abc123/messages").mock(
                return_value=httpx.Response(400, json={"error": {"message": "bad template"}})
            )
            with pytest.raises(WhatsAppSendError, match="whatsapp_api_status_400"):
                await send_template(
                    to_phone_e164="+212600000001",
                    template_name="jumlaos_otp",
                    language_code="ar_MA",
                    body_params=["123456"],
                )


# ---------------------------------------------------------------------------
# F07 — SMS adapter
# ---------------------------------------------------------------------------


class TestSmsAdapter:
    @pytest.mark.asyncio
    async def test_provider_none_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SMS_PROVIDER", "none")
        get_settings.cache_clear()
        with pytest.raises(SmsSendError, match="sms_provider_not_configured"):
            await send_sms(to_phone_e164="+212600000001", body="hi")

    @pytest.mark.asyncio
    async def test_twilio_missing_credentials_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SMS_PROVIDER", "twilio")
        monkeypatch.setenv("SMS_ACCOUNT_SID", "")
        monkeypatch.setenv("SMS_AUTH_TOKEN", "")
        monkeypatch.setenv("SMS_FROM_NUMBER", "")
        get_settings.cache_clear()
        with pytest.raises(SmsSendError, match="twilio_credentials_missing"):
            await send_sms(to_phone_e164="+212600000001", body="hi")

    @pytest.mark.asyncio
    async def test_twilio_happy_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SMS_PROVIDER", "twilio")
        monkeypatch.setenv("SMS_ACCOUNT_SID", "AC123")
        monkeypatch.setenv("SMS_AUTH_TOKEN", "token")
        monkeypatch.setenv("SMS_FROM_NUMBER", "+15555550000")
        get_settings.cache_clear()

        with respx.mock(base_url="https://api.twilio.com") as mock:
            route = mock.post("/2010-04-01/Accounts/AC123/Messages.json").mock(
                return_value=httpx.Response(201, json={"sid": "SM1"})
            )
            await send_sms(to_phone_e164="+212600000001", body="JumlaOS code: 123456")

        assert route.called
        body = route.calls.last.request.read().decode()
        assert "To=%2B212600000001" in body
        assert "From=%2B15555550000" in body

    @pytest.mark.asyncio
    async def test_twilio_4xx_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SMS_PROVIDER", "twilio")
        monkeypatch.setenv("SMS_ACCOUNT_SID", "AC123")
        monkeypatch.setenv("SMS_AUTH_TOKEN", "token")
        monkeypatch.setenv("SMS_FROM_NUMBER", "+15555550000")
        get_settings.cache_clear()

        with respx.mock(base_url="https://api.twilio.com") as mock:
            mock.post("/2010-04-01/Accounts/AC123/Messages.json").mock(
                return_value=httpx.Response(401, json={"message": "auth"})
            )
            with pytest.raises(SmsSendError, match="sms_provider_status_401"):
                await send_sms(to_phone_e164="+212600000001", body="hi")

    @pytest.mark.asyncio
    async def test_unsupported_provider_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Bypass pydantic validation by patching the settings instance directly,
        # since the field is a Literal["twilio", "none"].
        monkeypatch.setenv("SMS_PROVIDER", "twilio")
        get_settings.cache_clear()
        s = get_settings()
        # type: ignore is acceptable here only inside test mutation; we use
        # object.__setattr__ instead to satisfy the no-Any rule.
        object.__setattr__(s, "sms_provider", "messagebird")
        with pytest.raises(SmsSendError, match="unsupported_sms_provider"):
            await send_sms(to_phone_e164="+212600000001", body="hi")


# ---------------------------------------------------------------------------
# F07 — OTP transport dispatcher
# ---------------------------------------------------------------------------


class TestOtpTransportDispatch:
    @pytest.mark.asyncio
    async def test_log_transport_is_noop(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setenv("OTP_TRANSPORT", "log")
        get_settings.cache_clear()
        # Should return without calling Procrastinate or any HTTP.
        await deliver_otp(phone_e164="+212600000001", code="123456")

    @pytest.mark.asyncio
    async def test_unsupported_transport_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OTP_TRANSPORT", "log")
        get_settings.cache_clear()
        s = get_settings()
        object.__setattr__(s, "otp_transport", "carrier_pigeon")
        with pytest.raises(ValueError, match="unsupported_otp_transport"):
            await deliver_otp(phone_e164="+212600000001", code="123456")
