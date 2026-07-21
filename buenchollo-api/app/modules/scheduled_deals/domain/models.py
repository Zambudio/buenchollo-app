import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Index, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

import app.modules.categories.domain.models  # noqa: F401
import app.modules.deals.domain.models  # noqa: F401
import app.modules.stores.domain.models  # noqa: F401


class ScheduledDealStatus(str, Enum):
    SCHEDULED = "programado"
    PUBLISHED = "publicado"
    CANCELLED_PRICE = "cancelado_precio"
    CANCELLED_STOCK = "cancelado_stock"
    ERROR = "error"


class ScheduledDeal(Base):
    __tablename__ = "scheduled_deals"
    __table_args__ = (
        Index("ix_scheduled_deals_status_scheduled_at", "status", "scheduled_at"),
    )

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    deal_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    asin: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description_web: Mapped[str] = mapped_column(Text, default="", nullable=False)
    telegram_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    telegram_channel_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    offer_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    regular_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    discount_percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    affiliate_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    store_name: Mapped[str] = mapped_column(String(100), default="Amazon", nullable=False)
    category_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[ScheduledDealStatus] = mapped_column(
        SqlEnum(
            ScheduledDealStatus,
            name="scheduled_deal_status",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=ScheduledDealStatus.SCHEDULED,
        nullable=False,
    )
    cancellation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    deal = relationship("Deal")
    category = relationship("Category")
