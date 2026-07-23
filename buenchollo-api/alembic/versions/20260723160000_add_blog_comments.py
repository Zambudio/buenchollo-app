"""add blog_comments and blog_comment_votes tables

Revision ID: 20260723160000
Revises: 20260722210000
Create Date: 2026-07-23
"""
import sqlalchemy as sa
from alembic import op

revision = "20260723160000"
down_revision = "20260722210000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "blog_comments",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("blog_post_id", sa.dialects.postgresql.UUID(as_uuid=False), sa.ForeignKey("blog_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("parent_id", sa.dialects.postgresql.UUID(as_uuid=False), sa.ForeignKey("blog_comments.id", ondelete="CASCADE"), nullable=True),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("votes_up", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("votes_down", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_blog_comments_blog_post_id", "blog_comments", ["blog_post_id"])
    op.create_index("ix_blog_comments_parent_id", "blog_comments", ["parent_id"])

    op.create_table(
        "blog_comment_votes",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("comment_id", sa.dialects.postgresql.UUID(as_uuid=False), sa.ForeignKey("blog_comments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("vote", sa.SmallInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("comment_id", "user_id"),
    )

    # Recalcula votes_up/votes_down en blog_comments cada vez que cambia
    # blog_comment_votes — el router no lo hace en Python (mismo patrón que
    # comment_votes → deal_comments).
    op.execute("""
        CREATE OR REPLACE FUNCTION public.recalc_blog_comment_votes()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        DECLARE _c UUID;
        BEGIN
          _c := COALESCE(NEW.comment_id, OLD.comment_id);
          UPDATE public.blog_comments SET
            votes_up = (SELECT COUNT(*) FROM public.blog_comment_votes WHERE comment_id = _c AND vote = 1),
            votes_down = (SELECT COUNT(*) FROM public.blog_comment_votes WHERE comment_id = _c AND vote = -1)
          WHERE id = _c;
          RETURN COALESCE(NEW, OLD);
        END;
        $$;
    """)
    op.execute("DROP TRIGGER IF EXISTS blog_comment_votes_recalc ON public.blog_comment_votes;")
    op.execute("""
        CREATE TRIGGER blog_comment_votes_recalc
          AFTER INSERT OR UPDATE OR DELETE ON public.blog_comment_votes
          FOR EACH ROW EXECUTE FUNCTION public.recalc_blog_comment_votes();
    """)

    # RLS: tablas internas del backend, mismo patrón que blog_posts/blog_categories
    # (deny-all para anon/authenticated; el backend usa service_role y bypassa RLS).
    op.execute("ALTER TABLE public.blog_comments ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.blog_comment_votes ENABLE ROW LEVEL SECURITY;")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS blog_comment_votes_recalc ON public.blog_comment_votes;")
    op.execute("DROP FUNCTION IF EXISTS public.recalc_blog_comment_votes();")
    op.drop_table("blog_comment_votes")
    op.drop_index("ix_blog_comments_parent_id", table_name="blog_comments")
    op.drop_index("ix_blog_comments_blog_post_id", table_name="blog_comments")
    op.drop_table("blog_comments")
