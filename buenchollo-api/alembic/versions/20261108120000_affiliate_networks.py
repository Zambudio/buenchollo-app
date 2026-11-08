"""Redes de afiliación (Awin / Tradedoubler): registro de programas por tienda,
catálogo local de feeds y procedencia/evidencia de precio en los chollos.

Los programas se siembran como referencias SIN verificar: adhesión `unknown`,
deshabilitados y sin permiso de imágenes. El propietario los activa tras
comprobarlos (docs/guides/AFFILIATE-NETWORKS.md).

Revision ID: 20261108120000
Revises: 20261107120000
"""

import json
import uuid

import sqlalchemy as sa
from alembic import op

revision = "20261108120000"
down_revision = "20261107120000"
branch_labels = None
depends_on = None

_DISCLOSURE = "Enlace de afiliado: podemos recibir una comisión sin coste extra para ti."

_SEED = [
    # (network, advertiser_id, name, domains, store_name_like, notes, restrictions)
    ("awin", "20982", "PcComponentes", ["pccomponentes.com"], "pccomponentes", None, {}),
    ("awin", "124624", "Coolmod", ["coolmod.com"], "coolmod", None, {}),
    ("awin", "77630", "Fnac ES", ["fnac.es"], "fnac", None, {}),
    ("awin", "21707", "Samsung ES", ["samsung.com/es"], "samsung", "Solo la tienda española (samsung.com/es).", {}),
    (
        "awin",
        "37166",
        "Miravia (influencers / redes sociales)",
        ["miravia.es"],
        "miravia",
        "Programa para influencers y redes sociales. Su ficha remite otros modelos al 37168. "
        "No se elige automáticamente: el editor pide escoger.",
        {"marketplace": True, "third_party_sellers": "Marketplace con vendedores terceros"},
    ),
    (
        "awin",
        "37168",
        "Miravia (otros modelos de publisher)",
        ["miravia.es"],
        "miravia",
        "Programa al que remite la ficha del 37166 para otros modelos. No se elige automáticamente.",
        {"marketplace": True, "third_party_sellers": "Marketplace con vendedores terceros"},
    ),
    (
        "tradedoubler",
        "270504",
        "MediaMarkt ES",
        ["mediamarkt.es"],
        "mediamarkt",
        None,
        {
            "notes": "MediaMarkt restringe el uso de imágenes externas a Tradedoubler: verificar las "
            "condiciones del programa antes de habilitar imágenes en web/Telegram."
        },
    ),
]


def upgrade() -> None:
    op.create_table(
        "affiliate_programs",
        sa.Column("id", sa.UUID(as_uuid=False), primary_key=True),
        sa.Column("network", sa.String(16), nullable=False),
        sa.Column("advertiser_id", sa.String(32), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("store_id", sa.UUID(as_uuid=False), sa.ForeignKey("stores.id", ondelete="SET NULL"), nullable=True),
        sa.Column("domains", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("country", sa.String(2), nullable=False, server_default="ES"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="EUR"),
        sa.Column("membership_status", sa.String(16), nullable=False, server_default="unknown"),
        sa.Column("membership_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("membership_source", sa.String(16), nullable=True),
        sa.Column("promo_spaces", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("feeds", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("supports_import", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("supports_links", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("deeplink_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("restrictions", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("disclosure_text", sa.String(300), nullable=True),
        sa.Column("max_data_age_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("network", "advertiser_id", name="uq_affiliate_programs_network_advertiser"),
    )
    op.execute("ALTER TABLE public.affiliate_programs ENABLE ROW LEVEL SECURITY")

    op.create_table(
        "affiliate_feed_products",
        sa.Column("id", sa.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "program_id",
            sa.UUID(as_uuid=False),
            sa.ForeignKey("affiliate_programs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("feed_id", sa.String(32), nullable=False),
        sa.Column("generation", sa.BigInteger(), nullable=False),
        sa.Column("product_key", sa.String(64), nullable=False),
        sa.Column("merchant_product_id", sa.String(128), nullable=True),
        sa.Column("normalized_url", sa.String(2048), nullable=True),
        sa.Column("merchant_url", sa.String(2048), nullable=True),
        sa.Column("tracking_url", sa.String(2048), nullable=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("brand", sa.String(120), nullable=True),
        sa.Column("model", sa.String(120), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ean", sa.String(32), nullable=True),
        sa.Column("mpn", sa.String(64), nullable=True),
        sa.Column("colour", sa.String(64), nullable=True),
        sa.Column("condition", sa.String(32), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("rrp_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("delivery_cost", sa.String(64), nullable=True),
        sa.Column("in_stock", sa.Boolean(), nullable=True),
        sa.Column("image_url", sa.String(2048), nullable=True),
        sa.Column("category", sa.String(200), nullable=True),
        sa.Column("specs", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("provider_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("program_id", "feed_id", "generation", "product_key", name="uq_affiliate_feed_products_key"),
    )
    op.create_index("ix_affiliate_feed_products_url", "affiliate_feed_products", ["program_id", "normalized_url"])
    op.create_index("ix_affiliate_feed_products_ean", "affiliate_feed_products", ["program_id", "ean"])
    op.create_index("ix_affiliate_feed_products_mpid", "affiliate_feed_products", ["program_id", "merchant_product_id"])
    op.execute("ALTER TABLE public.affiliate_feed_products ENABLE ROW LEVEL SECURITY")

    op.add_column(
        "deals",
        sa.Column(
            "affiliate_program_id",
            sa.UUID(as_uuid=False),
            sa.ForeignKey("affiliate_programs.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("deals", sa.Column("data_source", sa.String(32), nullable=True))
    op.add_column("deals", sa.Column("data_provider_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("deals", sa.Column("data_imported_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("deals", sa.Column("price_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("deals", sa.Column("price_reference_type", sa.String(32), nullable=True))
    op.add_column("deals", sa.Column("price_reference_evidence", sa.String(500), nullable=True))
    op.add_column("deals", sa.Column("import_snapshot", sa.JSON(), nullable=True))

    conn = op.get_bind()
    for network, advertiser_id, name, domains, store_like, notes, restrictions in _SEED:
        restrictions = {"image_channels": [], **restrictions}
        conn.execute(
            sa.text(
                """
                INSERT INTO affiliate_programs
                    (id, network, advertiser_id, name, store_id, domains, restrictions, disclosure_text, notes)
                VALUES
                    (:id, :network, :advertiser_id, :name,
                     (SELECT s.id FROM stores s
                       WHERE lower(coalesce(s.domain, '')) LIKE :like OR lower(s.name) LIKE :like
                       ORDER BY s.created_at LIMIT 1),
                     CAST(:domains AS json), CAST(:restrictions AS json), :disclosure, :notes)
                ON CONFLICT (network, advertiser_id) DO NOTHING
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "network": network,
                "advertiser_id": advertiser_id,
                "name": name,
                "like": f"%{store_like}%",
                "domains": json.dumps(domains),
                "restrictions": json.dumps(restrictions),
                "disclosure": _DISCLOSURE,
                "notes": notes,
            },
        )


def downgrade() -> None:
    for column in (
        "import_snapshot",
        "price_reference_evidence",
        "price_reference_type",
        "price_verified_at",
        "data_imported_at",
        "data_provider_updated_at",
        "data_source",
        "affiliate_program_id",
    ):
        op.drop_column("deals", column)
    op.drop_table("affiliate_feed_products")
    op.drop_table("affiliate_programs")
