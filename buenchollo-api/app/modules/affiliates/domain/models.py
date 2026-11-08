"""Registro de programas de afiliación por tienda y catálogo local de feeds.

`AffiliateProgram` = relación de nuestra cuenta de publisher con un anunciante
en una red (Awin, Tradedoubler). Una tienda puede tener varios programas (p. ej.
Miravia 37166 / 37168): nunca se elige uno automáticamente si hay más de uno.

`AffiliateFeedProduct` = fila de un feed de producto sincronizado. Se escribe
por "generación": una sincronización inserta la generación nueva y, solo si
termina bien, borra la anterior. Un fallo nunca deja el feed vacío.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base

import app.modules.stores.domain.models  # noqa: F401  (FK stores.id)

NETWORK_AWIN = "awin"
NETWORK_TRADEDOUBLER = "tradedoubler"
NETWORKS = (NETWORK_AWIN, NETWORK_TRADEDOUBLER)

# Estado de adhesión al programa. Solo `joined` permite generar enlaces o publicar.
MEMBERSHIP_UNKNOWN = "unknown"
MEMBERSHIP_JOINED = "joined"
MEMBERSHIP_PENDING = "pending"
MEMBERSHIP_REJECTED = "rejected"
MEMBERSHIP_SUSPENDED = "suspended"
MEMBERSHIP_NOT_JOINED = "notjoined"
MEMBERSHIP_STATES = (
    MEMBERSHIP_UNKNOWN,
    MEMBERSHIP_JOINED,
    MEMBERSHIP_PENDING,
    MEMBERSHIP_REJECTED,
    MEMBERSHIP_SUSPENDED,
    MEMBERSHIP_NOT_JOINED,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AffiliateProgram(Base):
    __tablename__ = "affiliate_programs"
    __table_args__ = (UniqueConstraint("network", "advertiser_id", name="uq_affiliate_programs_network_advertiser"),)

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    network: Mapped[str] = mapped_column(String(16), nullable=False)
    # advertiserId (Awin) o program ID (Tradedoubler). Texto: ambos son numéricos
    # pero no se opera con ellos.
    advertiser_id: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    store_id: Mapped[str | None] = mapped_column(
        ForeignKey("stores.id", ondelete="SET NULL"), type_=Uuid(as_uuid=False), nullable=True
    )
    # Dominios exactos de la tienda (sin www). Un host casa si es igual o subdominio.
    domains: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    country: Mapped[str] = mapped_column(String(2), default="ES", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)

    membership_status: Mapped[str] = mapped_column(String(16), default=MEMBERSHIP_UNKNOWN, nullable=False)
    membership_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # api (consulta a la red) | manual (comprobado por el propietario en el panel de la red)
    membership_source: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # Espacios promocionales autorizados (web, telegram...) según la ficha del programa.
    promo_spaces: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    # Feeds conocidos: [{feed_id, name, language, selected, last_imported, products,
    # last_synced_at, last_synced_remote, last_status, last_error, rows}]. Nunca
    # guarda URLs de descarga (llevan la clave de feeds).
    feeds: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)

    supports_import: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    supports_links: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Tradedoubler: deeplink sin ficha solo si el propietario confirmó el formato
    # en el generador oficial de su cuenta (fecha en deeplink_verified_at).
    deeplink_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Restricciones: {"marketplace": bool|None, "third_party_sellers": str|None,
    # "image_channels": ["web","telegram"] | [], "channels": [...], "notes": str}
    restrictions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # Aviso adicional que exige el programa (se añade al post).
    disclosure_text: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # Antigüedad máxima de precio/stock antes de exigir revisión manual.
    max_data_age_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), default=_now
    )


class AffiliateFeedProduct(Base):
    __tablename__ = "affiliate_feed_products"
    __table_args__ = (
        UniqueConstraint("program_id", "feed_id", "generation", "product_key", name="uq_affiliate_feed_products_key"),
        Index("ix_affiliate_feed_products_url", "program_id", "normalized_url"),
        Index("ix_affiliate_feed_products_ean", "program_id", "ean"),
        Index("ix_affiliate_feed_products_mpid", "program_id", "merchant_product_id"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    program_id: Mapped[str] = mapped_column(
        ForeignKey("affiliate_programs.id", ondelete="CASCADE"), type_=Uuid(as_uuid=False), nullable=False
    )
    feed_id: Mapped[str] = mapped_column(String(32), nullable=False)
    generation: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Identidad estable del producto/variante en la red (aw_product_id).
    product_key: Mapped[str] = mapped_column(String(64), nullable=False)
    merchant_product_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    normalized_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    merchant_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    tracking_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ean: Mapped[str | None] = mapped_column(String(32), nullable=True)
    mpn: Mapped[str | None] = mapped_column(String(64), nullable=True)
    colour: Mapped[str | None] = mapped_column(String(64), nullable=True)
    condition: Mapped[str | None] = mapped_column(String(32), nullable=True)
    price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    rrp_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    delivery_cost: Mapped[str | None] = mapped_column(String(64), nullable=True)
    in_stock: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    category: Mapped[str | None] = mapped_column(String(200), nullable=True)
    specs: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    provider_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
