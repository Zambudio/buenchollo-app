"""Votos comunitarios al producto permanente para los tops de categoría.

Revision ID: 20261107120000
Revises: 20261106120000
"""

import sqlalchemy as sa
from alembic import op

revision = "20261107120000"
down_revision = "20261106120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_top_votes",
        sa.Column("id", sa.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", sa.UUID(as_uuid=False), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("product_id", "user_id", name="uq_product_top_votes_product_user"),
    )
    op.create_index("ix_product_top_votes_product_id", "product_top_votes", ["product_id"])
    op.create_index("ix_product_top_votes_user_id", "product_top_votes", ["user_id"])
    op.execute("ALTER TABLE public.product_top_votes ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("product_top_votes")
