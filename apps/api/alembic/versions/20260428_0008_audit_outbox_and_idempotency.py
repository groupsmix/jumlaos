"""F02/F15 idempotency_keys table + F03 audit_outbox + F19 refresh family_id

Revision ID: 0008_audit_outbox_idemp
Revises: 0007_procrastinate
Create Date: 2026-04-28 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008_audit_outbox_idemp"
down_revision = "0007_procrastinate"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # F02 + F15 — idempotency_keys table scoped by (business_id, user_id, key)
    # with same-TX response-storage support. user_id=0 means "anonymous /
    # pre-auth" requests; business_id=0 means "system / no-tenant".
    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("business_id", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("method", sa.String(8), nullable=False),
        sa.Column("path", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "business_id",
            "user_id",
            "idempotency_key",
            name="uq_idempotency_keys_scope",
        ),
    )

    # F03 — audit_outbox written on the caller's session in the same TX.
    # A Procrastinate task drains it into audit_log.
    op.create_table(
        "audit_outbox",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("business_id", sa.BigInteger(), nullable=True),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("actor_kind", sa.String(32), nullable=False, server_default="user"),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=True),
        sa.Column("before", postgresql.JSONB(), nullable=True),
        sa.Column("after", postgresql.JSONB(), nullable=True),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_audit_outbox_unprocessed",
        "audit_outbox",
        ["created_at"],
        postgresql_where=sa.text("processed_at IS NULL"),
    )

    # audit_outbox is multi-tenant: enforce RLS using the same policy as the
    # rest of the per-tenant tables. Bulk-drainer code that needs to read
    # cross-tenant rows runs with ``app.business_id = 'system'``.
    op.execute("ALTER TABLE audit_outbox ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_outbox FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON audit_outbox
        USING (
            current_setting('app.business_id', true) = 'system'
            OR business_id IS NULL
            OR business_id::text = current_setting('app.business_id', true)
        )
        """
    )

    # F19 — refresh-token reuse detection requires a family_id so that on
    # presentation of a revoked jti we can revoke every descendant.
    op.add_column(
        "refresh_tokens",
        sa.Column("family_id", postgresql.UUID(as_uuid=False), nullable=True),
    )
    op.add_column(
        "refresh_tokens",
        sa.Column("revoked_reason", sa.String(64), nullable=True),
    )
    op.create_index("ix_refresh_tokens_family", "refresh_tokens", ["family_id"])

    # Backfill existing tokens with a fresh family per row (worst case: each
    # surviving session is its own root). Cast to text via gen_random_uuid().
    op.execute(
        "UPDATE refresh_tokens SET family_id = gen_random_uuid()::text WHERE family_id IS NULL"
    )
    op.alter_column("refresh_tokens", "family_id", nullable=False)

    # F11 — stricter append-only triggers.
    # debt_events / payments: forbid any UPDATE outside the void whitelist.
    # invoices: forbid changing financial fields once status != 'draft'.
    op.execute("DROP TRIGGER IF EXISTS prevent_tampering_debt_events ON debt_events")
    op.execute("DROP TRIGGER IF EXISTS prevent_tampering_payments ON payments")
    op.execute("DROP TRIGGER IF EXISTS prevent_tampering_invoices ON invoices")
    op.execute("DROP FUNCTION IF EXISTS prevent_financial_tampering()")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_financial_tampering()
        RETURNS trigger AS $$
        DECLARE
            forbidden_changed boolean := false;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Cannot delete from append-only financial table %',
                    TG_TABLE_NAME;
            END IF;

            IF TG_OP = 'UPDATE' THEN
                IF TG_TABLE_NAME = 'debt_events' THEN
                    IF NEW.business_id IS DISTINCT FROM OLD.business_id
                       OR NEW.debtor_id IS DISTINCT FROM OLD.debtor_id
                       OR NEW.kind IS DISTINCT FROM OLD.kind
                       OR NEW.amount_centimes IS DISTINCT FROM OLD.amount_centimes
                       OR NEW.due_date IS DISTINCT FROM OLD.due_date
                       OR NEW.reference IS DISTINCT FROM OLD.reference
                       OR NEW.raw_message IS DISTINCT FROM OLD.raw_message
                       OR NEW.source IS DISTINCT FROM OLD.source
                       OR NEW.created_by_user_id IS DISTINCT FROM OLD.created_by_user_id
                       OR NEW.created_at IS DISTINCT FROM OLD.created_at
                       OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key THEN
                        forbidden_changed := true;
                    END IF;
                    IF forbidden_changed THEN
                        RAISE EXCEPTION 'debt_events is append-only: only void* fields are mutable';
                    END IF;
                ELSIF TG_TABLE_NAME = 'payments' THEN
                    IF NEW.business_id IS DISTINCT FROM OLD.business_id
                       OR NEW.amount_centimes IS DISTINCT FROM OLD.amount_centimes
                       OR NEW.method IS DISTINCT FROM OLD.method
                       OR NEW.paid_at IS DISTINCT FROM OLD.paid_at
                       OR NEW.created_at IS DISTINCT FROM OLD.created_at
                       OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key THEN
                        forbidden_changed := true;
                    END IF;
                    IF forbidden_changed THEN
                        RAISE EXCEPTION 'payments is append-only: only void* fields are mutable';
                    END IF;
                ELSIF TG_TABLE_NAME = 'invoices' THEN
                    IF OLD.status <> 'draft' AND (
                        NEW.subtotal_centimes IS DISTINCT FROM OLD.subtotal_centimes
                        OR NEW.vat_centimes IS DISTINCT FROM OLD.vat_centimes
                        OR NEW.total_centimes IS DISTINCT FROM OLD.total_centimes
                        OR NEW.currency IS DISTINCT FROM OLD.currency
                        OR NEW.debtor_id IS DISTINCT FROM OLD.debtor_id
                    ) THEN
                        RAISE EXCEPTION 'invoice financial fields are immutable once issued';
                    END IF;
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    for table in ("debt_events", "payments", "invoices"):
        op.execute(
            f"""
            CREATE TRIGGER prevent_tampering_{table}
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION prevent_financial_tampering();
            """
        )


def downgrade() -> None:
    for table in ("debt_events", "payments", "invoices"):
        op.execute(f"DROP TRIGGER IF EXISTS prevent_tampering_{table} ON {table}")
    op.execute("DROP FUNCTION IF EXISTS prevent_financial_tampering()")

    op.drop_index("ix_refresh_tokens_family", table_name="refresh_tokens")
    op.drop_column("refresh_tokens", "revoked_reason")
    op.drop_column("refresh_tokens", "family_id")

    op.drop_index("ix_audit_outbox_unprocessed", table_name="audit_outbox")
    op.drop_table("audit_outbox")
    op.drop_table("idempotency_keys")
