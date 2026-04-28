"""SMS fallback adapter (F07).

Provider-neutral interface — currently supports a Twilio-compatible REST
API. Configure via ``SMS_PROVIDER``, ``SMS_ACCOUNT_SID``, ``SMS_AUTH_TOKEN``,
``SMS_FROM_NUMBER``.
"""

from __future__ import annotations

import httpx

from jumlaos.config import get_settings
from jumlaos.logging import get_logger

log = get_logger(__name__)


class SmsSendError(RuntimeError):
    """Raised when the SMS provider rejects an outbound message."""


async def send_sms(*, to_phone_e164: str, body: str) -> None:
    settings = get_settings()
    if settings.sms_provider == "none":
        raise SmsSendError("sms_provider_not_configured")

    if settings.sms_provider == "twilio":
        if not (settings.sms_account_sid and settings.sms_auth_token and settings.sms_from_number):
            raise SmsSendError("twilio_credentials_missing")
        url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.sms_account_sid}/Messages.json"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                auth=(settings.sms_account_sid, settings.sms_auth_token),
                data={
                    "To": to_phone_e164,
                    "From": settings.sms_from_number,
                    "Body": body,
                },
            )
        if resp.status_code >= 400:
            log.error("sms_send_failed", status=resp.status_code, body=resp.text[:500])
            raise SmsSendError(f"sms_provider_status_{resp.status_code}")
        return

    raise SmsSendError(f"unsupported_sms_provider_{settings.sms_provider}")
