import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, String, Integer, Numeric, ForeignKey, DateTime, JSON, Uuid, SmallInteger, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base

# Importar Profile para que SQLAlchemy registre la tabla 'profiles' antes de resolver la FK created_by
import app.modules.users.domain.models  # noqa: F401

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
