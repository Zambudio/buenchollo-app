"""Catálogo permanente: products, product_listings y estado de oferta en deals.

Los chollos dejan de borrarse: la tarea `price_check` pasa a actualizar precio
y estado a diario. Cada deal existente se vincula a un producto y a su listing
(producto en una tienda) sin perder votos, comentarios ni favoritos.

Revision ID: 20261105120000
Revises: 20261103140000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261105120000"
down_revision = "20261103140000"
branch_labels = None
depends_on = None


_UUID = sa.UUID(as_uuid=False)

# Agrupa los deals sin producto por (tienda, ASIN en mayúsculas); los que no
# tienen identificador externo forman un grupo propio. Representante = el
# publicado más recientemente. Idempotente: solo toca deals sin product_id.
_BACKFILL_SQL = [
    "DROP TABLE IF EXISTS _cat_groups",
    "DROP TABLE IF EXISTS _cat_rep",
    """
    CREATE TEMP TABLE _cat_groups AS
    SELECT d.id AS deal_id,
           CASE WHEN nullif(btrim(d.external_id), '') IS NOT NULL
                THEN coalesce(d.store_id::text, '-') || ':' || upper(btrim(d.external_id))
                ELSE d.id::text END AS g,
           d.published_at,
           d.status
    FROM deals d
    WHERE d.product_id IS NULL
    """,
    """
    CREATE TEMP TABLE _cat_rep AS
    SELECT DISTINCT ON (g) g, deal_id AS rep_id,
           gen_random_uuid() AS product_id,
           gen_random_uuid() AS listing_id
    FROM _cat_groups
    ORDER BY g, published_at DESC NULLS LAST, deal_id
    """,
    """
    INSERT INTO products (id, slug, title, brand, description, short_description,
                          image_url, images, category_id, subcategory_id, status,
                          created_at, updated_at)
    SELECT r.product_id,
           CASE WHEN EXISTS (SELECT 1 FROM products p WHERE p.slug = d.slug)
                THEN d.slug || '-' || left(r.product_id::text, 8) ELSE d.slug END,
           d.title, d.brand, d.description, d.short_description, d.image_url,
           coalesce(d.images::jsonb, '[]'::jsonb), d.category_id, d.subcategory_id, 'active',
           coalesce(d.created_at, now()), now()
    FROM _cat_rep r JOIN deals d ON d.id = r.rep_id
    """,
    """
    INSERT INTO product_listings (id, product_id, store_id, source, external_id,
                                  canonical_url, affiliate_url, current_price,
                                  reference_price, discount_percentage, availability,
                                  created_at, updated_at)
    SELECT r.listing_id, r.product_id, d.store_id,
           CASE WHEN d.canonical_url ILIKE '%amazon.%' OR d.affiliate_url ILIKE '%amazon.%'
                     OR s.name ILIKE 'amazon%'
                THEN 'amazon' ELSE 'manual' END,
           upper(nullif(btrim(d.external_id), '')),
           d.canonical_url, d.affiliate_url, d.current_price, d.previous_price,
           d.discount_percentage, 'unknown', now(), now()
    FROM _cat_rep r
    JOIN deals d ON d.id = r.rep_id
    LEFT JOIN stores s ON s.id = d.store_id
    """,
    """
    UPDATE deals d
    SET product_id = r.product_id,
        listing_id = r.listing_id,
        offer_price = coalesce(d.offer_price, d.current_price)
    FROM _cat_groups g JOIN _cat_rep r ON r.g = g.g
    WHERE d.id = g.deal_id
    """,
    # Un mismo listing con varios deals activos: solo el más reciente sigue en oferta.
    """
    UPDATE deals d
    SET status = 'expired', offer_end_reason = 'manual'
    FROM (
        SELECT deal_id,
               row_number() OVER (PARTITION BY g ORDER BY published_at DESC NULLS LAST, deal_id) AS rn
        FROM _cat_groups WHERE status = 'active'
    ) ranked
    WHERE d.id = ranked.deal_id AND ranked.rn > 1
    """,
    "DROP TABLE _cat_groups",
    "DROP TABLE _cat_rep",
]


def backfill_catalog(connection) -> None:
    """Expuesta para el test de integración (recibe una conexión síncrona)."""
    for statement in _BACKFILL_SQL:
        connection.execute(sa.text(statement))


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("slug", sa.String(), nullable=False, unique=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("brand", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("short_description", sa.String(), nullable=True),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("images", postgresql.JSONB(), nullable=True),
        sa.Column("category_id", _UUID, sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("subcategory_id", _UUID, sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("gtin", sa.String(14), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("ALTER TABLE public.products ENABLE ROW LEVEL SECURITY")

    op.create_table(
        "product_listings",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", _UUID, sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("store_id", _UUID, sa.ForeignKey("stores.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source", sa.String(16), nullable=False, server_default="manual"),
        # Sin límite: deals.external_id tampoco lo tiene y el backfill no puede fallar.
        sa.Column("external_id", sa.String(), nullable=True),
        sa.Column("canonical_url", sa.String(), nullable=True),
        sa.Column("affiliate_url", sa.String(), nullable=True),
        sa.Column("current_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("reference_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("discount_percentage", sa.Integer(), nullable=True),
        sa.Column("in_stock", sa.Boolean(), nullable=True),
        sa.Column("availability", sa.String(16), nullable=False, server_default="unknown"),
        sa.Column("unavailable_since", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("store_id", "external_id", name="uq_product_listings_store_external"),
    )
    op.create_index("ix_product_listings_product_id", "product_listings", ["product_id"])
    op.create_index(
        "ix_product_listings_source_availability", "product_listings", ["source", "availability"]
    )
    op.execute("ALTER TABLE public.product_listings ENABLE ROW LEVEL SECURITY")

    op.add_column("deals", sa.Column("product_id", _UUID, nullable=True))
    op.add_column("deals", sa.Column("listing_id", _UUID, nullable=True))
    op.add_column("deals", sa.Column("offer_end_reason", sa.String(32), nullable=True))
    op.add_column("deals", sa.Column("offer_price", sa.Numeric(10, 2), nullable=True))
    op.add_column("deals", sa.Column("last_price_check_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("deals", sa.Column("admin_notified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("deals", sa.Column("admin_notified_price", sa.Numeric(10, 2), nullable=True))
    op.create_foreign_key(
        "deals_product_id_fkey", "deals", "products", ["product_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "deals_listing_id_fkey", "deals", "product_listings", ["listing_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index("ix_deals_product_id", "deals", ["product_id"])
    op.create_index("ix_deals_listing_id", "deals", ["listing_id"])

    op.add_column(
        "scheduled_task_run_items",
        sa.Column("transition", sa.String(16), nullable=False, server_default="offer_ended"),
    )
    # Marca de ejecución en curso (exclusión mutua entre el worker y el panel).
    op.add_column("scheduled_tasks", sa.Column("running_since", sa.DateTime(timezone=True), nullable=True))

    backfill_catalog(op.get_bind())

    # La revisión de precios pasa a diaria y activa; respeta la tolerancia ya
    # configurada y añade los nuevos parámetros si no existen.
    op.execute(
        """
        UPDATE scheduled_tasks
        SET enabled = true,
            frequency_preset = 'daily',
            config = ('{"min_discount_percent": 5, "purge_after_days": 30}'::jsonb
                      || coalesce(config::jsonb, '{}'::jsonb))::json
        WHERE task_type = 'price_check'
        """
    )


def downgrade() -> None:
    # El código anterior BORRA los chollos que revisa: al volver atrás se
    # desactiva la tarea para que no limpie de golpe el catálogo acumulado.
    op.execute(
        "UPDATE scheduled_tasks SET enabled = false, frequency_preset = 'weekly' "
        "WHERE task_type = 'price_check'"
    )
    op.drop_column("scheduled_tasks", "running_since")
    op.drop_column("scheduled_task_run_items", "transition")
    op.drop_index("ix_deals_listing_id", table_name="deals")
    op.drop_index("ix_deals_product_id", table_name="deals")
    op.drop_constraint("deals_listing_id_fkey", "deals", type_="foreignkey")
    op.drop_constraint("deals_product_id_fkey", "deals", type_="foreignkey")
    for column in (
        "admin_notified_price",
        "admin_notified_at",
        "last_price_check_at",
        "offer_price",
        "offer_end_reason",
        "listing_id",
        "product_id",
    ):
        op.drop_column("deals", column)
    op.drop_table("product_listings")
    op.drop_table("products")
