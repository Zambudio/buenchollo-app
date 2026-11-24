"""Instagram: cola de publicaciones del feed y cuenta conectada (token).

Revision ID: 20261124130000
Revises: 20261124120000
"""

import sqlalchemy as sa
from alembic import op

revision = "20261124130000"
down_revision = "20261124120000"
branch_labels = None
depends_on = None

_UUID = sa.UUID(as_uuid=False)


def upgrade() -> None:
    op.create_table(
        "instagram_posts",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("deal_id", _UUID, sa.ForeignKey("deals.id", ondelete="SET NULL"), nullable=True),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("image", sa.LargeBinary(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("container_id", sa.String(64), nullable=True),
        sa.Column("media_id", sa.String(64), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'published', 'error')", name="ck_instagram_posts_status"),
    )
    op.create_index("ix_instagram_posts_status_created", "instagram_posts", ["status", "created_at"])
    op.create_table(
        "instagram_account",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("seed_hash", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(64), nullable=True),
        sa.Column("username", sa.String(100), nullable=True),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("alerted_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Sin políticas: solo la API (conexión directa) las lee. El token nunca por PostgREST.
    op.execute("ALTER TABLE public.instagram_posts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.instagram_account ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("instagram_account")
    op.drop_table("instagram_posts")
