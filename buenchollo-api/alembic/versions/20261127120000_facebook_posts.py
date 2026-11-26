"""Facebook: cola de publicaciones de la página y fuente `facebook` en la analítica.

Revision ID: 20261127120000
Revises: 20261126120000
"""

import sqlalchemy as sa
from alembic import op

revision = "20261127120000"
down_revision = "20261126120000"
branch_labels = None
depends_on = None

_UUID = sa.UUID(as_uuid=False)
_SOURCE = "ck_analytics_events_source"


def upgrade() -> None:
    op.create_table(
        "facebook_posts",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("deal_id", _UUID, sa.ForeignKey("deals.id", ondelete="SET NULL"), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("image", sa.LargeBinary(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("post_id", sa.String(100), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'published', 'error')", name="ck_facebook_posts_status"),
    )
    op.create_index("ix_facebook_posts_status_created", "facebook_posts", ["status", "created_at"])
    # Sin políticas: solo la API (conexión directa) la lee.
    op.execute("ALTER TABLE public.facebook_posts ENABLE ROW LEVEL SECURITY")

    # /facebook redirige con utm_source=facebook: esas visitas se cuentan aparte.
    op.drop_constraint(_SOURCE, "analytics_events", type_="check")
    op.create_check_constraint(
        _SOURCE,
        "analytics_events",
        "source IN ('telegram', 'whatsapp', 'instagram', 'facebook', 'organic', 'referral', 'direct')",
    )


def downgrade() -> None:
    op.execute("UPDATE analytics_events SET source = 'referral' WHERE source = 'facebook'")
    op.drop_constraint(_SOURCE, "analytics_events", type_="check")
    op.create_check_constraint(
        _SOURCE, "analytics_events", "source IN ('telegram', 'whatsapp', 'instagram', 'organic', 'referral', 'direct')"
    )
    op.drop_table("facebook_posts")
