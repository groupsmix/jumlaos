"""Outbound WhatsApp Cloud API adapter (F07).

Sends a WhatsApp template message via Meta's Cloud API. The function is sync
in shape but uses ``httpx.AsyncClient`` under the hood — call it from
``await``.

It is the *only* place in the codebase that knows about Meta's HTTP shape;
the rest of the app deals in ``send_template(to, name, params)``.
"""

from __future__ import annotations

from typing import Any

import httpx

from jumlaos.config import get_settings
from jumlaos.logging import get_logger

GRAPH_API_VERSION = "v20.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

log = get_logger(__name__)


class WhatsAppSendError(RuntimeError):
    """Raised when the Cloud API rejects an outbound message."""


async def send_template(
    *,
    to_phone_e164: str,
    template_name: str,
    language_code: str,
    body_params: list[str],
) -> dict[str, Any]:
    """Send a templated WhatsApp message.

    The phone number must be in E.164 format with the leading ``+``. Meta
    accepts both ``+212600000001`` and ``212600000001`` — we strip the ``+``
    to normalise.
    """
    settings = get_settings()
    if not (settings.whatsapp_phone_number_id and settings.whatsapp_access_token):
        raise WhatsAppSendError("whatsapp_credentials_missing")

    url = f"{GRAPH_BASE}/{settings.whatsapp_phone_number_id}/messages"
    payload: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": to_phone_e164.lstrip("+"),
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": p} for p in body_params],
                }
            ],
        },
    }
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, headers=headers, json=payload)

    if resp.status_code >= 400:
        log.error(
            "whatsapp_send_failed",
            status=resp.status_code,
            template=template_name,
            body=resp.text[:500],
        )
        raise WhatsAppSendError(f"whatsapp_api_status_{resp.status_code}")

    data: dict[str, Any] = resp.json()
    return data
