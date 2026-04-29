"""Meta WhatsApp Cloud API webhook handlers."""

from __future__ import annotations

import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jumlaos.config import get_settings
from jumlaos.core.deps import db
from jumlaos.core.models import Business
from jumlaos.core.rate_limit import ip_key, limiter
from jumlaos.logging import get_logger
from jumlaos.talab.models import WaInboundMessage

router = APIRouter()
log = get_logger(__name__)


@router.get("/webhook/whatsapp", include_in_schema=False)
async def verify_subscription(
    mode: str = Query(alias="hub.mode"),
    token: str = Query(alias="hub.verify_token"),
    challenge: str = Query(alias="hub.challenge"),
) -> str:
    """Meta calls this once when you subscribe. Returns `challenge` as-is."""
    settings = get_settings()
    if mode == "subscribe" and token == settings.whatsapp_webhook_verify_token:
        return challenge
    raise HTTPException(status_code=403, detail="verification_failed")


def _verify_signature(body: bytes, signature_header: str | None, secret: str) -> bool:
    if not signature_header or not secret:
        return False
    try:
        algo, sig = signature_header.split("=", 1)
    except ValueError:
        return False
    if algo != "sha256":
        return False
    mac = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, sig)


@router.post("/webhook/whatsapp")
@limiter.limit("100/second", key_func=ip_key)
async def whatsapp_inbound(
    request: Request,
    session: AsyncSession = Depends(db),
) -> dict[str, str]:
    """Receive WhatsApp inbound messages.

    Stores the raw payload for replay-safety before any state mutation.
    Parsing is done asynchronously by a Procrastinate worker (see
    `jumlaos.workers`).
    """
    settings = get_settings()
    body = await request.body()

    if not settings.whatsapp_app_secret and not settings.is_dev:
        raise HTTPException(status_code=500, detail="missing_secret_in_prod")

    if settings.whatsapp_app_secret:
        if not _verify_signature(
            body, request.headers.get("x-hub-signature-256"), settings.whatsapp_app_secret
        ):
            raise HTTPException(status_code=403, detail="bad_signature")
    else:
        log.warning("whatsapp_webhook_signature_skipped_in_dev")

    try:
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="bad_json") from exc

    count = 0
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value") or {}
            messages = value.get("messages") or []
            for msg in messages:
                wa_id = msg.get("id")
                from_phone = msg.get("from")
                if not wa_id or not from_phone:
                    continue

                phone_number_id = value.get("metadata", {}).get("phone_number_id")
                if not phone_number_id:
                    log.warning("wa_inbound_missing_phone_number_id", wa_id=wa_id)
                    continue

                business_id = (
                    await session.execute(
                        select(Business.id).where(
                            Business.whatsapp_phone_number_id == phone_number_id
                        )
                    )
                ).scalar_one_or_none()

                if not business_id:
                    log.warning("wa_inbound_business_not_found", phone_number_id=phone_number_id)
                    continue

                # Replay-safe: unique index on wa_message_id rejects duplicates.
                existing = (
                    await session.execute(
                        select(WaInboundMessage).where(WaInboundMessage.wa_message_id == wa_id)
                    )
                ).scalar_one_or_none()
                if existing is not None:
                    continue

                phone_e164 = from_phone if from_phone.startswith("+") else f"+{from_phone}"
                session.add(
                    WaInboundMessage(
                        business_id=business_id,
                        wa_message_id=wa_id,
                        from_phone_e164=phone_e164,
                        raw_payload=msg,
                        message_type=msg.get("type", "unknown"),
                    )
                )
                count += 1

    log.info("wa_inbound_received", count=count)
    return {"status": "ok"}
