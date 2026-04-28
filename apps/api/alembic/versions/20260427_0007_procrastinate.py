"""Add procrastinate schema

Revision ID: 0007_procrastinate
Revises: 0006_debtor_ice
Create Date: 2026-04-27 00:00:06.000000
"""

from __future__ import annotations

from alembic import op
import procrastinate
from jumlaos.config import get_settings

revision = "0007_procrastinate"
down_revision = "0006_debtor_ice"
branch_labels = None
depends_on = None


def upgrade() -> None:
    settings = get_settings()
    app = procrastinate.App(
        connector=procrastinate.AiopgConnector(
            dsn=settings.database_url_sync,
        ),
    )
    schema_manager = procrastinate.schema.SchemaManager(app.connector)
    op.execute(schema_manager.get_schema())


def downgrade() -> None:
    # Downgrading procrastinate schema is complex and usually skipped
    pass
