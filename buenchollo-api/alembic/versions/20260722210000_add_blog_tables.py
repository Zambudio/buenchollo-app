"""add blog_categories and blog_posts tables

Revision ID: 20260722210000
Revises: 20260721163000
Create Date: 2026-07-22
"""
import sqlalchemy as sa
from alembic import op

revision = "20260722210000"
down_revision = "20260721163000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "blog_categories",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False, unique=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "blog_posts",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("slug", sa.String(), nullable=False, unique=True),
        sa.Column("excerpt", sa.String(), nullable=True),
        sa.Column("content", sa.dialects.postgresql.JSONB(), nullable=False, server_default=sa.text("'{\"type\": \"doc\", \"content\": []}'::jsonb")),
        sa.Column("cover_image_url", sa.String(), nullable=True),
        sa.Column("cover_image_alt", sa.String(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("category_id", sa.dialects.postgresql.UUID(as_uuid=False), sa.ForeignKey("blog_categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tags", sa.dialects.postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("author_id", sa.dialects.postgresql.UUID(as_uuid=False), sa.ForeignKey("profiles.user_id", ondelete="SET NULL"), nullable=True),
        sa.Column("seo_title", sa.String(), nullable=True),
        sa.Column("seo_description", sa.String(), nullable=True),
        sa.Column("canonical_url", sa.String(), nullable=True),
        sa.Column("og_image_url", sa.String(), nullable=True),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_blog_posts_status_published_at", "blog_posts", ["status", "published_at"])
    op.create_index("ix_blog_posts_category_published_at", "blog_posts", ["category_id", "published_at"])
    op.create_index("ix_blog_posts_featured_published_at", "blog_posts", ["is_featured", "published_at"])

    # RLS: tablas internas del backend. El service_role bypassa RLS y los
    # endpoints (público + admin) son el único punto de acceso; el frontend
    # nunca consulta estas tablas directamente (ADR-002). Sin políticas =
    # deny-all por defecto para anon/authenticated (mismo patrón que
    # admin_audit_log, ADR-006).
    op.execute("ALTER TABLE public.blog_categories ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.blog_posts ENABLE ROW LEVEL SECURITY;")


def downgrade() -> None:
    op.drop_index("ix_blog_posts_featured_published_at", table_name="blog_posts")
    op.drop_index("ix_blog_posts_category_published_at", table_name="blog_posts")
    op.drop_index("ix_blog_posts_status_published_at", table_name="blog_posts")
    op.drop_table("blog_posts")
    op.drop_table("blog_categories")
