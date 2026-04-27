"""initial schema

Revision ID: 0001_init
Revises:
Create Date: 2026-04-27 00:00:00.000000

This migration is generated and reviewed by hand. Subsequent migrations
should use `alembic revision --autogenerate` and require code review.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("phone_e164", sa.String(20), nullable=False, unique=True),
        sa.Column("display_name", sa.String(100)),
        sa.Column("locale", sa.String(8), nullable=False, server_default="ar-MA"),
        sa.Column("otp_lockout_until", sa.DateTime(timezone=True)),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_users_phone_e164", "users", ["phone_e164"], unique=True)

    business_plan = postgresql.ENUM("mali", "mali_talab", "full", name="business_plan")
    business_plan.create(op.get_bind(), checkfirst=True)
    business_status = postgresql.ENUM("active", "suspended", "terminated", name="business_status")
    business_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "businesses",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "owner_user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False, index=True
        ),
        sa.Column("legal_name", sa.String(200), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("phone_e164", sa.String(20), nullable=False, unique=True),
        sa.Column("ice_number", sa.String(20)),
        sa.Column("rc_number", sa.String(50)),
        sa.Column("if_number", sa.String(50)),
        sa.Column("cnss_number", sa.String(50)),
        sa.Column("dgi_taxpayer_id", sa.String(50)),
        sa.Column("city", sa.String(100)),
        sa.Column("region", sa.String(100)),
        sa.Column("plan", business_plan, nullable=False, server_default="mali"),
        sa.Column("status", business_status, nullable=False, server_default="active"),
        sa.Column(
            "modules_enabled",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("""'{"mali": true, "talab": false, "makhzen": false}'::jsonb"""),
        ),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    membership_role = postgresql.ENUM(
        "owner", "manager", "staff", "accountant", "driver", name="membership_role"
    )
    membership_role.create(op.get_bind(), checkfirst=True)
    membership_status = postgresql.ENUM("active", "revoked", name="membership_status")
    membership_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "memberships",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "business_id",
            sa.BigInteger(),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("role", membership_role, nullable=False),
        sa.Column(
            "permissions",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("status", membership_status, nullable=False, server_default="active"),
        sa.Column("invited_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id")),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("user_id", "business_id", name="uq_memberships_user_bus"),
    )

    op.create_table(
        "otp_codes",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("phone_e164", sa.String(20), nullable=False),
        sa.Column("code_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("ip", sa.String(45)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_otp_phone_active", "otp_codes", ["phone_e164", "consumed_at"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "business_id", sa.BigInteger(), sa.ForeignKey("businesses.id", ondelete="SET NULL")
        ),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("actor_kind", sa.String(32), nullable=False, server_default="user"),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(64)),
        sa.Column("before", postgresql.JSONB()),
        sa.Column("after", postgresql.JSONB()),
        sa.Column("ip", sa.String(45)),
        sa.Column("user_agent", sa.Text()),
        sa.Column("request_id", sa.String(64)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_audit_business_created", "audit_log", ["business_id", "created_at"])
    op.create_index("ix_audit_entity", "audit_log", ["entity_type", "entity_id"])
    op.create_index("ix_audit_log_request_id", "audit_log", ["request_id"])

    op.create_table(
        "domain_events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "business_id",
            sa.BigInteger(),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column(
            "payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "emitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("processing_error", sa.Text()),
    )
    op.create_index(
        "ix_domain_events_business_kind_emitted", "domain_events", ["business_id", "kind"]
    )

    op.create_table(
        "webhook_dlq",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column(
            "received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "headers", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("body", sa.LargeBinary(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )

    sub_plan = postgresql.ENUM("mali", "mali_talab", "full", name="subscription_plan")
    sub_plan.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "business_id",
            sa.BigInteger(),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("plan", sub_plan, nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="trialing"),
        sa.Column("provider", sa.String(32), nullable=False, server_default="cmi"),
        sa.Column("last_payment_reference", sa.String(128)),
        sa.Column("auto_renew", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # ---- Mali tables ----
    op.create_table(
        "debtors",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "business_id",
            sa.BigInteger(),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("phone_e164", sa.String(20), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("alias_normalized", sa.String(200), nullable=False),
        sa.Column("city", sa.String(100)),
        sa.Column("address_text", sa.Text()),
        sa.Column("credit_limit_centimes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("payment_terms_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("risk_score", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("business_id", "phone_e164", name="uq_debtors_business_phone"),
    )
    op.create_index("ix_debtors_business_alias", "debtors", ["business_id", "alias_normalized"])

    debt_event_kind = postgresql.ENUM(
        "debt", "payment", "adjustment", "writeoff", "refund", name="debt_event_kind"
    )
    debt_event_kind.create(op.get_bind(), checkfirst=True)
    debt_event_source = postgresql.ENUM(
        "whatsapp", "web", "order", "import", name="debt_event_source"
    )
    debt_event_source.create(op.get_bind(), checkfirst=True)
    invoice_status = postgresql.ENUM(
        "draft", "issued", "paid", "partial", "void", name="invoice_status"
    )
    invoice_status.create(op.get_bind(), checkfirst=True)
    payment_method = postgresql.ENUM(
        "cash", "bank_transfer", "cheque", "cmi", "cashplus", "other", name="payment_method"
    )
    payment_method.create(op.get_bind(), checkfirst=True)
    tax_period_status = postgresql.ENUM("open", "closed", name="tax_period_status")
    tax_period_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "invoices",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "business_id",
            sa.BigInteger(),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("debtor_id", sa.BigInteger(), sa.ForeignKey("debtors.id", ondelete="SET NULL")),
        sa.Column("number", sa.String(32)),
        sa.Column("issued_at", sa.DateTime(timezone=True)),
        sa.Column("due_at", sa.Date()),
        sa.Column("status", invoice_status, nullable=False, server_default="draft"),
        sa.Column("subtotal_centimes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("vat_centimes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_centimes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("payment_terms_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="MAD"),
        sa.Column("pdf_r2_key", sa.String(300)),
        sa.Column("created_by_user_id", sa.BigInteger()),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("business_id", "number", name="uq_invoices_business_number"),
    )
    op.create_index("ix_invoices_business_status", "invoices", ["business_id", "status"])

    op.create_table(
        "invoice_lines",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "invoice_id",
            sa.BigInteger(),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("product_id", sa.BigInteger()),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("qty", sa.Numeric(14, 4), nullable=False),
        sa.Column("unit_price_centimes", sa.BigInteger(), nullable=False),
        sa.Column("vat_rate_bps", sa.Integer(), nullable=False, server_default="2000"),
        sa.Column("line_subtotal_centimes", sa.BigInteger(), nullable=False),
    )

    op.create_table(
        "invoice_number_counters",
        sa.Column(
            "business_id",
            sa.BigInteger(),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("year", sa.Integer(), primary_key=True),
        sa.Column("last_seq", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "debt_events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "business_id",
            sa.BigInteger(),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "debtor_id",
            sa.BigInteger(),
            sa.ForeignKey("debtors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", debt_event_kind, nullable=False),
        sa.Column("amount_centimes", sa.BigInteger(), nullable=False),
        sa.Column("due_date", sa.Date()),
        sa.Column("reference", sa.String(128)),
        sa.Column("source", debt_event_source, nullable=False, server_default="web"),
        sa.Column("raw_message", sa.Text()),
        sa.Column(
            "related_invoice_id",
            sa.BigInteger(),
            sa.ForeignKey("invoices.id", ondelete="SET NULL"),
        ),
        sa.Column("related_order_id", sa.BigInteger()),
        sa.Column("voided", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("voided_reason", sa.String(200)),
        sa.Column("voided_at", sa.DateTime(timezone=True)),
        sa.Column("voided_by_user_id", sa.BigInteger()),
        sa.Column("created_by_user_id", sa.BigInteger()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_debt_events_bd_created", "debt_events", ["business_id", "debtor_id", "created_at"]
    )
    op.create_index(
        "ix_debt_events_due",
        "debt_events",
        ["business_id", "due_date"],
        postgresql_where=sa.text("kind = 'debt' AND voided = false"),
    )

    op.create_table(
        "debt_balances",
        sa.Column(
            "business_id",
            sa.BigInteger(),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "debtor_id",
            sa.BigInteger(),
            sa.ForeignKey("debtors.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "total_outstanding_centimes", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column("oldest_unpaid_due_date", sa.Date()),
        sa.Column("days_past_due", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_payment_at", sa.DateTime(timezone=True)),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "business_id",
            sa.BigInteger(),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("debtor_id", sa.BigInteger(), sa.ForeignKey("debtors.id", ondelete="SET NULL")),
        sa.Column("invoice_id", sa.BigInteger(), sa.ForeignKey("invoices.id", ondelete="SET NULL")),
        sa.Column("method", payment_method, nullable=False),
        sa.Column("amount_centimes", sa.BigInteger(), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reference", sa.String(128)),
        sa.Column("attachment_r2_key", sa.String(300)),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_payments_business_debtor", "payments", ["business_id", "debtor_id"])

    op.create_table(
        "reminders",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "business_id",
            sa.BigInteger(),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "debtor_id",
            sa.BigInteger(),
            sa.ForeignKey("debtors.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("invoice_id", sa.BigInteger(), sa.ForeignKey("invoices.id", ondelete="SET NULL")),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("template_name", sa.String(64), nullable=False),
        sa.Column("locale", sa.String(8), nullable=False, server_default="ar-MA"),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(64)),
        sa.Column("wa_message_id", sa.String(128)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    op.create_table(
        "tax_periods",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "business_id",
            sa.BigInteger(),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("status", tax_period_status, nullable=False, server_default="open"),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("closed_by_user_id", sa.BigInteger()),
        sa.Column("csv_export_r2_key", sa.String(300)),
        sa.Column(
            "extra", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("business_id", "period_start", name="uq_tax_periods_business_start"),
    )

    # ---- Talab + Makhzen tables: created in later migrations as those modules
    # come online. For now we keep the schema minimal to ship Mali at week 10.


def downgrade() -> None:
    """Drop everything. Money tables are append-only in prod; downgrades are
    only used in dev/CI."""
    for t in (
        "tax_periods",
        "reminders",
        "payments",
        "debt_balances",
        "debt_events",
        "invoice_number_counters",
        "invoice_lines",
        "invoices",
        "debtors",
        "subscriptions",
        "webhook_dlq",
        "domain_events",
        "audit_log",
        "otp_codes",
        "memberships",
        "businesses",
        "users",
    ):
        op.drop_table(t)
    for enum_name in (
        "tax_period_status",
        "payment_method",
        "invoice_status",
        "debt_event_source",
        "debt_event_kind",
        "subscription_plan",
        "membership_status",
        "membership_role",
        "business_status",
        "business_plan",
    ):
        postgresql.ENUM(name=enum_name).drop(op.get_bind(), checkfirst=True)
