"""OTP delivery dispatch (F07).

Reads ``settings.otp_transport`` and either:

* logs the OTP (dev/test only) — never in prod/staging (config validator
  refuses to boot prod with ``OTP_TRANSPORT=log``),
* enqueues a WhatsApp template send via Procrastinate, or
* enqueues an SMS send via Procrastinate.

The handler stays sync from the caller's perspective: enqueue and return.
The actual third-party call happens on the worker, with retries.
"""

from __future__ import annotations

from jumlaos.config import get_settings
from jumlaos.logging import get_logger

log = get_logger(__name__)

# Meta WhatsApp template that carries the OTP. Must be approved in the
# Meta business manager. The body has one variable: {{1}} = code.
OTP_TEMPLATE_NAME = "jumlaos_otp"
OTP_TEMPLATE_LANG = "ar_MA"


async def deliver_otp(*, phone_e164: str, code: str) -> None:
    settings = get_settings()
    transport = settings.otp_transport

    if transport == "log":
        # Dev / test only.
        log.info("otp_delivered_via_log", phone=phone_e164, code=code)
        return

    # Lazy import to avoid circular imports at module load and to keep the
    # web layer free of worker-app instantiation.
    from jumlaos.workers.tasks import send_otp_sms, send_otp_whatsapp

    if transport == "whatsapp":
        await send_otp_whatsapp.defer_async(phone_e164=phone_e164, code=code)
        return

    if transport == "sms":
        await send_otp_sms.defer_async(phone_e164=phone_e164, code=code)
        return

    raise ValueError(f"unsupported_otp_transport_{transport}")
