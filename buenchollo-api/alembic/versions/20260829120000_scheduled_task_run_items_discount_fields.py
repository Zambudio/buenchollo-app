"""add discount and short description to scheduled_task_run_items

Revision ID: 20260829120000
Revises: 20260809120000
Create Date: 2026-08-29
"""
from alembic import op
import sqlalchemy as sa


revision = "20260829120000"
down_revision = "20260809120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scheduled_task_run_items", sa.Column("previous_price", sa.Numeric(10, 2), nullable=True))
    op.add_column("scheduled_task_run_items", sa.Column("discount_percentage", sa.Integer(), nullable=True))
    op.add_column("scheduled_task_run_items", sa.Column("short_description", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("scheduled_task_run_items", "short_description")
    op.drop_column("scheduled_task_run_items", "discount_percentage")
    op.drop_column("scheduled_task_run_items", "previous_price")
