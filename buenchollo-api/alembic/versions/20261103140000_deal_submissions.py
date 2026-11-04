"""Add deal_submissions, deals.coupon_code and deals.canonical_url.

Revision ID: 20261103140000
Revises: 20261103120000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261103140000"
down_revision = "20261103120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deal_submissions",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("profiles.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("affiliate_url", sa.Text(), nullable=False),
        sa.Column("asin", sa.String(16), nullable=True),
        sa.Column("store_id", sa.UUID(), sa.ForeignKey("stores.id", ondelete="SET NULL"), nullable=True),
        sa.Column("store_name", sa.String(80), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("current_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("previous_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("coupon_code", sa.String(64), nullable=True),
        sa.Column("shipping_info", sa.String(120), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("category_id", sa.UUID(), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("subcategory_id", sa.UUID(), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("images", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("warnings", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("rejection_reason", sa.String(500), nullable=True),
        sa.Column("reviewed_by", sa.UUID(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deal_id", sa.UUID(), sa.ForeignKey("deals.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending','approved','rejected','withdrawn')",
            name="ck_deal_submissions_status",
        ),
        sa.CheckConstraint(
            "previous_price IS NULL OR previous_price > current_price",
            name="ck_deal_submissions_previous_price",
        ),
    )
    op.create_index("ix_deal_submissions_status_created", "deal_submissions", ["status", "created_at"])
    op.create_index("ix_deal_submissions_user_created", "deal_submissions", ["user_id", "created_at"])
    op.create_index(
        "uq_deal_submissions_pending_asin",
        "deal_submissions",
        ["asin"],
        unique=True,
        postgresql_where=sa.text("status = 'pending' AND asin IS NOT NULL"),
    )
    op.create_index(
        "uq_deal_submissions_pending_canonical",
        "deal_submissions",
        ["canonical_url"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.execute("ALTER TABLE public.deal_submissions ENABLE ROW LEVEL SECURITY")

    op.add_column("deals", sa.Column("coupon_code", sa.String(64), nullable=True))
    op.add_column("deals", sa.Column("canonical_url", sa.Text(), nullable=True))
    op.create_index("ix_deals_canonical_url", "deals", ["canonical_url"])


def downgrade() -> None:
    op.drop_index("ix_deals_canonical_url", table_name="deals")
    op.drop_column("deals", "canonical_url")
    op.drop_column("deals", "coupon_code")
    op.drop_table("deal_submissions")
