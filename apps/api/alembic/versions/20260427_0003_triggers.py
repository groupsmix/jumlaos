"""Add triggers to prevent financial tampering

Revision ID: 0003_triggers
Revises: 0002_rls
Create Date: 2026-04-27 00:00:02.000000
"""

from __future__ import annotations

from alembic import op

revision = "0003_triggers"
down_revision = "0002_rls"
branch_labels = None
depends_on = None


def upgrade() -> None:
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


def downgrade() -> None:
    for table in ("debt_events", "payments", "invoices"):
        op.execute(f"DROP TRIGGER IF EXISTS prevent_tampering_{table} ON {table}")
    op.execute("DROP FUNCTION IF EXISTS prevent_financial_tampering()")
