"""Add RLS policies

Revision ID: 0002_rls
Revises: 0001_init
Create Date: 2026-04-27 00:00:01.000000
"""

from __future__ import annotations

from alembic import op

revision = "0002_rls"
down_revision = "0001_init"
branch_labels = None
depends_on = None

TABLES = [
    "audit_log",
    "domain_events",
    "subscriptions",
    "debtors",
    "invoices",
    "invoice_number_counters",
    "debt_events",
    "debt_balances",
    "payments",
    "reminders",
    "tax_periods",
    "warehouses",
    "products",
    "stock_lots",
    "stock_movements",
    "order_intakes",
    "orders",
    "wa_inbound_messages",
]


def upgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        # Policy allows access if app.business_id matches, OR if app.business_id is 'system' (for background jobs),
        # OR if business_id is NULL (for unassigned records like raw webhooks)
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (
                current_setting('app.business_id', true) = 'system'
                OR business_id IS NULL
                OR business_id::text = current_setting('app.business_id', true)
            )
        """)


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
