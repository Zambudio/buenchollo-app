"""create scheduled deals publication queue

Revision ID: 20260720120000
Revises: 20260709120000
Create Date: 2026-07-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260720120000"
down_revision = "20260709120000"
branch_labels = None
depends_on = None


scheduled_status = postgresql.ENUM(
    "programado",
    "publicado",
    "cancelado_precio",
    "cancelado_stock",
    "error",
    name="scheduled_deal_status",
    create_type=False,
)


def upgrade() -> None:
    scheduled_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "scheduled_deals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("deal_id", sa.Uuid(), nullable=False),
        sa.Column("asin", sa.String(length=10), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description_web", sa.Text(), nullable=False),
        sa.Column("telegram_text", sa.Text(), nullable=False),
        sa.Column("offer_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("regular_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("discount_percentage", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(length=2048), nullable=True),
        sa.Column("affiliate_url", sa.String(length=2048), nullable=False),
        sa.Column("store_name", sa.String(length=100), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", scheduled_status, server_default="programado", nullable=False),
        sa.Column("cancellation_reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deal_id"),
    )
    op.create_index(
        "ix_scheduled_deals_status_scheduled_at",
        "scheduled_deals",
        ["status", "scheduled_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_scheduled_deals_status_scheduled_at", table_name="scheduled_deals")
    op.drop_table("scheduled_deals")
    scheduled_status.drop(op.get_bind(), checkfirst=True)
