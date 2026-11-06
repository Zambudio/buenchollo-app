"""Registro de publicaciones de Telegram (texto, imagen, canal y precios).

Revision ID: 20261106120000
Revises: 20261105120000
"""

import sqlalchemy as sa
from alembic import op

revision = "20261106120000"
down_revision = "20261105120000"
branch_labels = None
depends_on = None

_UUID = sa.UUID(as_uuid=False)


def upgrade() -> None:
    op.create_table(
        "telegram_publications",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("deal_id", _UUID, sa.ForeignKey("deals.id", ondelete="CASCADE"), nullable=True),
        sa.Column("channel_id", sa.String(100), nullable=False),
        sa.Column("channel_kind", sa.String(16), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("image_url", sa.String(2048), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=True),
        sa.Column("previous_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("discount_percentage", sa.Integer(), nullable=True),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=True),
        sa.Column("sent_by", _UUID, sa.ForeignKey("profiles.user_id", ondelete="SET NULL"), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_telegram_publications_deal_sent", "telegram_publications", ["deal_id", "sent_at"])
    op.execute("ALTER TABLE public.telegram_publications ENABLE ROW LEVEL SECURITY")
    # Aviso de bajada de precio en ofertas activas (por defecto ≥ 5 %).
    op.execute(
        """
        UPDATE scheduled_tasks
        SET config = ('{"price_drop_percent": 5}'::jsonb || coalesce(config::jsonb, '{}'::jsonb))::json
        WHERE task_type = 'price_check'
        """
    )


def downgrade() -> None:
    op.execute(
        "UPDATE scheduled_tasks SET config = (config::jsonb - 'price_drop_percent')::json "
        "WHERE task_type = 'price_check'"
    )
    op.drop_table("telegram_publications")
