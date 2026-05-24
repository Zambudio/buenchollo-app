import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Numeric, Boolean, ForeignKey, DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    keyword: Mapped[str | None] = mapped_column(String(200), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)

    category_id: Mapped[str | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), type_=Uuid(as_uuid=False), nullable=True
    )
    store_id: Mapped[str | None] = mapped_column(
        ForeignKey("stores.id", ondelete="SET NULL"), type_=Uuid(as_uuid=False), nullable=True
    )

    min_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    max_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    min_discount: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), default="instant", nullable=False)
    notify_email: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notify_in_app: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
        default=lambda: datetime.now(timezone.utc)
    )

    category = relationship("Category", foreign_keys=[category_id])
    store = relationship("Store", foreign_keys=[store_id])
