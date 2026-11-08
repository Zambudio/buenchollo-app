import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, String, Integer, Numeric, ForeignKey, DateTime, JSON, Uuid, SmallInteger, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base

# Importar Profile para que SQLAlchemy registre la tabla 'profiles' antes de resolver la FK created_by
import app.modules.users.domain.models  # noqa: F401
# FK product_id / listing_id al catálogo permanente
import app.modules.catalog.domain.models  # noqa: F401
# FK affiliate_program_id al registro de programas de afiliación
import app.modules.affiliates.domain.models  # noqa: F401

class Deal(Base):
    __tablename__ = "deals"
    __table_args__ = (
        Index("ix_deals_status_published_at", "status", "published_at"),
        Index("ix_deals_status_temperature", "status", "temperature"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    short_description: Mapped[str | None] = mapped_column(String, nullable=True)
    
    current_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    previous_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    discount_percentage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    savings_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    images: Mapped[list[str]] = mapped_column(JSON, default=list)
    
    affiliate_url: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String, nullable=True)
    
    status: Mapped[str] = mapped_column(String, default="active")
    source: Mapped[str] = mapped_column(String, default="manual")
    
    temperature: Mapped[int] = mapped_column(Integer, default=0)
    votes_up: Mapped[int] = mapped_column(Integer, default=0)
    votes_down: Mapped[int] = mapped_column(Integer, default=0)
    click_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    favorite_count: Mapped[int] = mapped_column(Integer, default=0)
    
    brand: Mapped[str | None] = mapped_column(String, nullable=True)
    shipping_info: Mapped[str | None] = mapped_column(String, nullable=True)
    external_id: Mapped[str | None] = mapped_column(String, nullable=True)
    duplicate_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    show_keepa_chart: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    coupon_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    # Catálogo permanente: la oferta ya no se borra, cambia de estado. Guarda por
    # qué terminó, el precio con el que se publicó/reactivó por última vez
    # (`offer_price`, referencia de las reglas de oferta) y el antispam del
    # aviso al canal Admin.
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), type_=Uuid(as_uuid=False), nullable=True, index=True)
    listing_id: Mapped[str | None] = mapped_column(ForeignKey("product_listings.id", ondelete="SET NULL"), type_=Uuid(as_uuid=False), nullable=True, index=True)
    offer_end_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    offer_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    last_price_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    admin_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    admin_notified_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Importación desde redes de afiliación (Awin / Tradedoubler). Procedencia y
    # antigüedad del dato, y qué significa el precio "antes" y con qué evidencia:
    # sin evidencia válida el chollo puede guardarse como borrador pero no publicarse.
    affiliate_program_id: Mapped[str | None] = mapped_column(
        ForeignKey("affiliate_programs.id", ondelete="SET NULL"), type_=Uuid(as_uuid=False), nullable=True
    )
    data_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    data_provider_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    data_imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    price_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    price_reference_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    price_reference_evidence: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Valores tal como llegaron en la última importación: al reimportar se
    # compara con ellos para no pisar en silencio lo que se editó a mano.
    import_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Foreign keys
    category_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), type_=Uuid(as_uuid=False), nullable=True)
    subcategory_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), type_=Uuid(as_uuid=False), nullable=True)
    store_id: Mapped[str | None] = mapped_column(ForeignKey("stores.id", ondelete="SET NULL"), type_=Uuid(as_uuid=False), nullable=True)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("profiles.user_id", ondelete="SET NULL"), type_=Uuid(as_uuid=False), nullable=True)
    
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), default=lambda: datetime.now(timezone.utc))

    # Relationships
    category = relationship("Category", foreign_keys=[category_id])
    subcategory = relationship("Category", foreign_keys=[subcategory_id])
    store = relationship("Store")
    author = relationship(
        "Profile",
        primaryjoin="Deal.created_by == Profile.user_id",
        foreign_keys="Deal.created_by",
        viewonly=True,
        # Solo se serializa vía `public_author`: si una query futura olvida el
        # selectinload, que falle en los tests en vez de un lazy-load async.
        lazy="raise_on_sql",
    )

    @property
    def public_author(self):
        return self.author if self.source == "community" else None


class DealVote(Base):
    __tablename__ = "deal_votes"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    deal_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("deals.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    vote: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("deal_id", "user_id"),)


class Favorite(Base):
    __tablename__ = "favorites"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    deal_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("deals.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    deal = relationship("Deal")

    __table_args__ = (UniqueConstraint("deal_id", "user_id"),)
