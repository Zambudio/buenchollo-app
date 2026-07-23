"""add votes_up/votes_down to blog_posts and blog_post_votes table

Revision ID: 20260723170000
Revises: 20260723160000
Create Date: 2026-07-23
"""
import sqlalchemy as sa
from alembic import op

revision = "20260723170000"
down_revision = "20260723160000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("blog_posts", sa.Column("votes_up", sa.Integer(), nullable=False, server_default=sa.text("0")))
    op.add_column("blog_posts", sa.Column("votes_down", sa.Integer(), nullable=False, server_default=sa.text("0")))

    op.create_table(
        "blog_post_votes",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("blog_post_id", sa.dialects.postgresql.UUID(as_uuid=False), sa.ForeignKey("blog_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("vote", sa.SmallInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("blog_post_id", "user_id"),
    )

    # RLS: tabla interna del backend, igual que blog_comment_votes (deny-all
    # para anon/authenticated; el backend usa service_role y recalcula
    # votes_up/votes_down en Python tras cada voto, sin trigger).
    op.execute("ALTER TABLE public.blog_post_votes ENABLE ROW LEVEL SECURITY;")


def downgrade() -> None:
    op.drop_table("blog_post_votes")
    op.drop_column("blog_posts", "votes_down")
    op.drop_column("blog_posts", "votes_up")
