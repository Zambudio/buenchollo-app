"""add first-party analytics and blog view counter

Revision ID: 20260926120000
Revises: 20260905121000
Create Date: 2026-09-26
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260926120000"
down_revision = "20260905121000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "blog_posts",
        sa.Column("view_count", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
    )

    op.create_table(
        "analytics_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("visitor_hash", sa.String(length=64), nullable=False),
        sa.Column("session_hash", sa.String(length=64), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column(
            "blog_post_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("blog_posts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("source_detail", sa.String(length=100), nullable=False),
        sa.Column("medium", sa.String(length=50), nullable=False),
        sa.Column("campaign", sa.String(length=100), nullable=True),
        sa.Column("referrer_host", sa.String(length=253), nullable=True),
        sa.CheckConstraint(
            "source IN ('telegram', 'organic', 'referral', 'direct')",
            name="ck_analytics_events_source",
        ),
        sa.CheckConstraint("char_length(path) BETWEEN 1 AND 500", name="ck_analytics_events_path"),
    )
    op.create_index("ix_analytics_events_occurred_at", "analytics_events", ["occurred_at"])
    op.create_index(
        "ix_analytics_events_source_occurred_at", "analytics_events", ["source", "occurred_at"]
    )
    op.create_index(
        "ix_analytics_events_visitor_occurred_at", "analytics_events", ["visitor_hash", "occurred_at"]
    )
    op.create_index(
        "ix_analytics_events_session_occurred_at", "analytics_events", ["session_hash", "occurred_at"]
    )
    op.create_index(
        "ix_analytics_events_blog_occurred_at", "analytics_events", ["blog_post_id", "occurred_at"]
    )

    op.create_table(
        "analytics_blog_daily_views",
        sa.Column(
            "blog_post_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("blog_posts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("visitor_hash", sa.String(length=64), primary_key=True),
        sa.Column("view_date", sa.Date(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_analytics_blog_daily_views_date", "analytics_blog_daily_views", ["view_date"]
    )
    op.create_index(
        "ix_analytics_blog_daily_views_visitor_date",
        "analytics_blog_daily_views",
        ["visitor_hash", "view_date"],
    )

    # Tablas internas: acceso exclusivo del API Gateway. Sin policies,
    # anon/authenticated quedan en deny-all; la conexión backend conserva acceso.
    op.execute("ALTER TABLE public.analytics_events ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.analytics_blog_daily_views ENABLE ROW LEVEL SECURITY;")


def downgrade() -> None:
    op.drop_index("ix_analytics_blog_daily_views_visitor_date", table_name="analytics_blog_daily_views")
    op.drop_index("ix_analytics_blog_daily_views_date", table_name="analytics_blog_daily_views")
    op.drop_table("analytics_blog_daily_views")
    op.drop_index("ix_analytics_events_blog_occurred_at", table_name="analytics_events")
    op.drop_index("ix_analytics_events_session_occurred_at", table_name="analytics_events")
    op.drop_index("ix_analytics_events_visitor_occurred_at", table_name="analytics_events")
    op.drop_index("ix_analytics_events_source_occurred_at", table_name="analytics_events")
    op.drop_index("ix_analytics_events_occurred_at", table_name="analytics_events")
    op.drop_table("analytics_events")
    op.drop_column("blog_posts", "view_count")
