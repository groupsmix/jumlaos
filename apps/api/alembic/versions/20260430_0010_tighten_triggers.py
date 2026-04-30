"""F11: tighten append-only triggers on financial tables

On debt_events and payments: reject any UPDATE except the void whitelist
(voided, voided_reason, voided_at, voided_by_user_id).

On invoices: reject UPDATE of subtotal_centimes, vat_centimes,
total_centimes, currency, debtor_id once status != 'draft'.

Revision ID: 0010_tighten_triggers
Revises: 0009_event_sub_offsets
Create Date: 2026-04-30 12:00:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "0010_tighten_triggers"
down_revision = "0009_event_sub_offsets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old permissive triggers first.
    for table in ("debt_events", "payments", "invoices"):
        op.execute(f"DROP TRIGGER IF EXISTS prevent_tampering_{table} ON {table}")
    op.execute("DROP FUNCTION IF EXISTS prevent_financial_tampering()")

    # -- debt_events: only allow UPDATE on the void whitelist columns.
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_debt_event_tampering()
        RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Cannot delete from append-only table debt_events';
            END IF;

            IF TG_OP = 'UPDATE' THEN
                -- Only the void-related columns may change.
                IF NEW.business_id      IS DISTINCT FROM OLD.business_id
                OR NEW.debtor_id        IS DISTINCT FROM OLD.debtor_id
                OR NEW.kind             IS DISTINCT FROM OLD.kind
                OR NEW.amount_centimes  IS DISTINCT FROM OLD.amount_centimes
                OR NEW.due_date         IS DISTINCT FROM OLD.due_date
                OR NEW.reference        IS DISTINCT FROM OLD.reference
                OR NEW.source           IS DISTINCT FROM OLD.source
                OR NEW.raw_message      IS DISTINCT FROM OLD.raw_message
                OR NEW.related_invoice_id IS DISTINCT FROM OLD.related_invoice_id
                OR NEW.related_order_id IS DISTINCT FROM OLD.related_order_id
                OR NEW.idempotency_key  IS DISTINCT FROM OLD.idempotency_key
                OR NEW.created_by_user_id IS DISTINCT FROM OLD.created_by_user_id
                OR NEW.created_at       IS DISTINCT FROM OLD.created_at
                THEN
                    RAISE EXCEPTION
                        'debt_events: only voided, voided_reason, voided_at, '
                        'voided_by_user_id may be updated';
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER prevent_tampering_debt_events
        BEFORE UPDATE OR DELETE ON debt_events
        FOR EACH ROW EXECUTE FUNCTION prevent_debt_event_tampering();
    """)

    # -- payments: only allow UPDATE on the void whitelist columns.
    # payments currently has no void columns, so forbid ALL updates.
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_payment_tampering()
        RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Cannot delete from append-only table payments';
            END IF;

            IF TG_OP = 'UPDATE' THEN
                RAISE EXCEPTION
                    'payments: updates are forbidden; '
                    'corrections must use reversal rows';
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER prevent_tampering_payments
        BEFORE UPDATE OR DELETE ON payments
        FOR EACH ROW EXECUTE FUNCTION prevent_payment_tampering();
    """)

    # -- invoices: reject UPDATE of financial fields once status != 'draft'.
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_invoice_tampering()
        RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Cannot delete from invoices';
            END IF;

            IF TG_OP = 'UPDATE' THEN
                IF OLD.status != 'draft' THEN
                    IF NEW.subtotal_centimes IS DISTINCT FROM OLD.subtotal_centimes
                    OR NEW.vat_centimes      IS DISTINCT FROM OLD.vat_centimes
                    OR NEW.total_centimes    IS DISTINCT FROM OLD.total_centimes
                    OR NEW.currency          IS DISTINCT FROM OLD.currency
                    OR NEW.debtor_id         IS DISTINCT FROM OLD.debtor_id
                    THEN
                        RAISE EXCEPTION
                            'invoices: cannot modify financial fields '
                            '(subtotal_centimes, vat_centimes, total_centimes, '
                            'currency, debtor_id) once status is not draft';
                    END IF;
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER prevent_tampering_invoices
        BEFORE UPDATE OR DELETE ON invoices
        FOR EACH ROW EXECUTE FUNCTION prevent_invoice_tampering();
    """)


def downgrade() -> None:
    for table in ("debt_events", "payments", "invoices"):
        op.execute(f"DROP TRIGGER IF EXISTS prevent_tampering_{table} ON {table}")
    op.execute("DROP FUNCTION IF EXISTS prevent_debt_event_tampering()")
    op.execute("DROP FUNCTION IF EXISTS prevent_payment_tampering()")
    op.execute("DROP FUNCTION IF EXISTS prevent_invoice_tampering()")

    # Restore original permissive trigger.
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_financial_tampering()
        RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Cannot delete from append-only financial table %', TG_TABLE_NAME;
            END IF;
            IF TG_OP = 'UPDATE' THEN
                IF TG_TABLE_NAME = 'debt_events' THEN
                    IF NEW.amount_centimes != OLD.amount_centimes OR NEW.kind != OLD.kind THEN
                        RAISE EXCEPTION 'Cannot modify financial amounts of a debt event';
                    END IF;
                ELSIF TG_TABLE_NAME = 'payments' THEN
                    IF NEW.amount_centimes != OLD.amount_centimes THEN
                        RAISE EXCEPTION 'Cannot modify financial amounts of a payment';
                    END IF;
                ELSIF TG_TABLE_NAME = 'invoices' THEN
                    IF OLD.status != 'draft' AND NEW.total_centimes != OLD.total_centimes THEN
                        RAISE EXCEPTION 'Cannot modify financial amounts of an issued invoice';
                    END IF;
                END IF;
                RETURN NEW;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    for table in ("debt_events", "payments", "invoices"):
        op.execute(f"""
            CREATE TRIGGER prevent_tampering_{table}
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION prevent_financial_tampering();
        """)
