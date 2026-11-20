"""Histórico de precios propio (`price_history`): un punto por listing y día.

Lo alimentan la revisión diaria de precios y las altas/ediciones de chollos, de
cualquier tienda. Se siembra con el precio actual de cada listing para no
empezar de cero.

Revision ID: 20261120120000
Revises: 20261118120000
"""

import sqlalchemy as sa
from alembic import op

revision = "20261120120000"
down_revision = "20261118120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "price_history",
        sa.Column("id", sa.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "listing_id",
            sa.UUID(as_uuid=False),
            sa.ForeignKey("product_listings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id", sa.UUID(as_uuid=False), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("store_id", sa.UUID(as_uuid=False), sa.ForeignKey("stores.id", ondelete="SET NULL"), nullable=True),
        sa.Column("observed_on", sa.Date(), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("low_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("reference_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("in_stock", sa.Boolean(), nullable=True),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("listing_id", "observed_on", name="uq_price_history_listing_day"),
    )
    op.create_index("ix_price_history_product_day", "price_history", ["product_id", "observed_on"])
    op.execute("ALTER TABLE public.price_history ENABLE ROW LEVEL SECURITY")
    # Semilla: el último precio conocido de cada listing, en el día de su última revisión.
    op.execute(
        """
        INSERT INTO price_history
            (listing_id, product_id, store_id, observed_on, price, low_price,
             reference_price, in_stock, source, observed_at)
        SELECT id, product_id, store_id,
               (COALESCE(last_checked_at, updated_at, now()) AT TIME ZONE 'Europe/Madrid')::date,
               current_price, current_price, reference_price, in_stock, 'backfill',
               COALESCE(last_checked_at, updated_at, now())
        FROM product_listings
        WHERE current_price IS NOT NULL AND current_price > 0
        ON CONFLICT (listing_id, observed_on) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("price_history")
