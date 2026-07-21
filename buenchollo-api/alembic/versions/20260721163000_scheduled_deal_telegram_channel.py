"""store the selected Telegram channel for scheduled publications

Revision ID: 20260721163000
Revises: 20260720120000
Create Date: 2026-07-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260721163000"
down_revision = "20260720120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scheduled_deals",
        sa.Column("telegram_channel_id", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scheduled_deals", "telegram_channel_id")
