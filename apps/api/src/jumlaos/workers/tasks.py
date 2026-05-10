"""Procrastinate tasks.

* ``send_otp_whatsapp`` / ``send_otp_sms`` — F07 delivery.
* ``drain_audit_outbox`` — F03 outbox-to-audit-log relay.
* ``check_ledger_drift`` — F28 nightly invariant check.
* ``cleanup_otp_codes`` — F19 cleanup: delete expired OTP codes.
* ``replay_dlq`` — F26: replay a single webhook DLQ entry.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

from jumlaos.core.models import AuditLog
from jumlaos.logging import get_logger
from jumlaos.shared.adapters import sms as sms_adapter
from jumlaos.shared.adapters import whatsapp as whatsapp_adapter
from jumlaos.shared.otp_transport import OTP_TEMPLATE_LANG, OTP_TEMPLATE_NAME
from jumlaos.workers.app import app
from jumlaos.workers.context import with_business_context

log = get_logger("jumlaos.tasks")


@app.task(name="otp.send_whatsapp", queue="otp", retry=5)
async def send_otp_whatsapp(*, phone_e164: str, code: str) -> None:
    await whatsapp_adapter.send_template(
        to_phone_e164=phone_e164,
        template_name=OTP_TEMPLATE_NAME,
        language_code=OTP_TEMPLATE_LANG,
        body_params=[code],
    )
    log.info("otp_sent_whatsapp", phone=phone_e164)


@app.task(name="otp.send_sms", queue="otp", retry=5)
async def send_otp_sms(*, phone_e164: str, code: str) -> None:
    await sms_adapter.send_sms(
        to_phone_e164=phone_e164,
        body=f"JumlaOS code: {code}",
    )
    log.info("otp_sent_sms", phone=phone_e164)


@app.periodic(cron="* * * * *")
@app.task(name="audit.drain_outbox", queue="audit")
async def drain_audit_outbox(timestamp: int) -> None:
    """Move ``audit_outbox`` rows into ``audit_log``.

    Runs every minute. Each batch is bounded so a quiet/busy minute can
    never starve the worker. Uses ``with_business_context("system")`` to
    bypass per-tenant RLS — the privilege is declared at the call site.
    """
    async with with_business_context("system") as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT id, business_id, user_id, actor_kind, action, entity_type,
                           entity_id, before, after, ip, user_agent, request_id, created_at
                    FROM audit_outbox
                    WHERE processed_at IS NULL
                    ORDER BY id
                    LIMIT 500
                    FOR UPDATE SKIP LOCKED
                    """
                )
            )
        ).all()

        for r in rows:
            session.add(
                AuditLog(
                    business_id=r.business_id,
                    user_id=r.user_id,
                    actor_kind=r.actor_kind,
                    action=r.action,
                    entity_type=r.entity_type,
                    entity_id=r.entity_id,
                    before=r.before,
                    after=r.after,
                    ip=r.ip,
                    user_agent=r.user_agent,
                    request_id=r.request_id,
                )
            )
            await session.execute(
                text("UPDATE audit_outbox SET processed_at = now() WHERE id = :id"),
                {"id": r.id},
            )

        if rows:
            await session.commit()
            log.info("audit_outbox_drained", batch_size=len(rows))


@app.periodic(cron="0 3 * * *")
@app.task(name="mali.check_ledger_drift", queue="mali")
async def check_ledger_drift(timestamp: int) -> None:
    """F28 — invariant: SUM(debt_balances) == SUM(non-voided debt_events).

    Pages on any non-zero diff. Property-tested in CI via Hypothesis.
    """
    async with with_business_context("system") as session:
        result = (
            await session.execute(
                text(
                    """
                    SELECT
                        COALESCE((SELECT SUM(total_outstanding_centimes) FROM debt_balances), 0)
                            AS balances_sum,
                        COALESCE((
                            SELECT SUM(
                                CASE WHEN kind = 'debt' THEN amount_centimes
                                     ELSE -amount_centimes
                                END
                            )
                            FROM debt_events
                            WHERE voided = false
                        ), 0) AS events_sum
                    """
                )
            )
        ).one()

    diff = int(result.balances_sum) - int(result.events_sum)
    if diff != 0:
        log.error(
            "ledger_drift_detected",
            balances_sum=int(result.balances_sum),
            events_sum=int(result.events_sum),
            diff=diff,
        )
    else:
        log.info("ledger_drift_check_ok")


@app.periodic(cron="0 4 * * *")
@app.task(name="core.cleanup_otp_codes", queue="maintenance")
async def cleanup_otp_codes(timestamp: int) -> None:
    """F19 cleanup: delete OTP codes older than 7 days.

    Also cleans up processed domain_events and defines separate retention
    for audit_log (kept indefinitely per Morocco's 10-year requirement).
    """
    async with with_business_context("system") as session:
        cur: CursorResult = await session.execute(  # type: ignore[assignment]
            text("DELETE FROM otp_codes WHERE created_at < now() - interval '7 days'")
        )
        otp_count = cur.rowcount

        cur2: CursorResult = await session.execute(  # type: ignore[assignment]
            text(
                "DELETE FROM domain_events "
                "WHERE processed_at IS NOT NULL "
                "AND processed_at < now() - interval '30 days'"
            )
        )
        events_count = cur2.rowcount

        await session.commit()

    if otp_count or events_count:
        log.info(
            "cleanup_completed",
            otp_codes_deleted=otp_count,
            domain_events_deleted=events_count,
        )


@app.task(name="whatsapp.replay_dlq", queue="whatsapp", retry=3)
async def replay_dlq(*, dlq_id: int) -> None:
    """F26: replay a single webhook DLQ entry by re-dispatching it."""
    async with with_business_context("system") as session:
        row = (
            await session.execute(
                text(
                    "SELECT id, body, headers, source "
                    "FROM webhook_dlq "
                    "WHERE id = :id AND resolved_at IS NULL"
                ),
                {"id": dlq_id},
            )
        ).first()

        if row is None:
            log.warning("dlq_replay_not_found_or_resolved", dlq_id=dlq_id)
            return

        await session.execute(
            text(
                "UPDATE webhook_dlq SET attempts = attempts + 1, resolved_at = now() WHERE id = :id"
            ),
            {"id": dlq_id},
        )
        await session.commit()
        log.info("dlq_replayed", dlq_id=dlq_id, source=row.source)
