"""Allow Telegram schedules while the linked web deal remains a draft.

Revision ID: 20261103120000
Revises: 20260926120000
"""

import sqlalchemy as sa
from alembic import op

revision = "20261103120000"
down_revision = "20260926120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scheduled_deals",
        sa.Column("web_ready", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column("scheduled_deals", "asin", existing_type=sa.String(10), nullable=True)
    op.alter_column(
        "scheduled_deals", "category_id", existing_type=sa.UUID(), nullable=True
    )


def downgrade() -> None:
    # PostgreSQL detendrá el downgrade si hay programaciones incompletas.
    op.alter_column("scheduled_deals", "category_id", existing_type=sa.UUID(), nullable=False)
    op.alter_column("scheduled_deals", "asin", existing_type=sa.String(10), nullable=False)
    op.drop_column("scheduled_deals", "web_ready")
