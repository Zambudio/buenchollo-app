"""Catálogo permanente: el producto (ficha que no se borra) y su presencia en
cada tienda (listing). Las ofertas siguen siendo `deals` y apuntan aquí."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

# FK a categories/stores: registrar las tablas antes de resolver las relaciones.
import app.modules.categories.domain.models  # noqa: F401
import app.modules.stores.domain.models  # noqa: F401

AVAILABLE = "available"
UNAVAILABLE = "unavailable"
NOT_FOUND = "not_found"
UNKNOWN = "unknown"

SOURCE_AMAZON = "amazon"
SOURCE_MANUAL = "manual"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    brand: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    short_description: Mapped[str | None] = mapped_column(String, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    images: Mapped[list[str]] = mapped_column(JSON, default=list)
    category_id: Mapped[str | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), type_=Uuid(as_uuid=False), nullable=True
    )
    subcategory_id: Mapped[str | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), type_=Uuid(as_uuid=False), nullable=True
    )
    gtin: Mapped[str | None] = mapped_column(String(14), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), default=_now
    )

    listings: Mapped[list["ProductListing"]] = relationship(
        "ProductListing", back_populates="product", cascade="all, delete-orphan", passive_deletes=True
    )


class ProductListing(Base):
    __tablename__ = "product_listings"
    __table_args__ = (
        UniqueConstraint("store_id", "external_id", name="uq_product_listings_store_external"),
        Index("ix_product_listings_source_availability", "source", "availability"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), type_=Uuid(as_uuid=False), nullable=False, index=True
    )
    store_id: Mapped[str | None] = mapped_column(
        ForeignKey("stores.id", ondelete="SET NULL"), type_=Uuid(as_uuid=False), nullable=True
    )
    source: Mapped[str] = mapped_column(String(16), default=SOURCE_MANUAL, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String, nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(String, nullable=True)
    affiliate_url: Mapped[str | None] = mapped_column(String, nullable=True)
    current_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    reference_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    discount_percentage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    in_stock: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    availability: Mapped[str] = mapped_column(String(16), default=UNKNOWN, nullable=False)
    unavailable_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), default=_now
    )

    product: Mapped[Product] = relationship("Product", back_populates="listings")
    store = relationship("Store")


class ProductTopVote(Base):
    __tablename__ = "product_top_votes"
    __table_args__ = (UniqueConstraint("product_id", "user_id", name="uq_product_top_votes_product_user"),)

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), type_=Uuid(as_uuid=False), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
