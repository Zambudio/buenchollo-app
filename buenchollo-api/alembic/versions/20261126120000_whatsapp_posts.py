"""WhatsApp: cola de publicaciones del Canal de WhatsApp.

Revision ID: 20261126120000
Revises: 20261124150000
"""

import sqlalchemy as sa
from alembic import op

revision = "20261126120000"
down_revision = "20261124150000"
branch_labels = None
depends_on = None

_UUID = sa.UUID(as_uuid=False)


def upgrade() -> None:
    op.create_table(
        "whatsapp_posts",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("deal_id", _UUID, sa.ForeignKey("deals.id", ondelete="SET NULL"), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("image", sa.LargeBinary(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message_id", sa.String(64), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("not_before", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'published', 'error')", name="ck_whatsapp_posts_status"),
    )
    op.create_index("ix_whatsapp_posts_status_created", "whatsapp_posts", ["status", "created_at"])
    op.create_index("ix_whatsapp_posts_published_at", "whatsapp_posts", ["published_at"])
    op.create_index("ix_whatsapp_posts_deal_id", "whatsapp_posts", ["deal_id"])
    # Sin políticas: solo la API (conexión directa) la lee.
    op.execute("ALTER TABLE public.whatsapp_posts ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("whatsapp_posts")
