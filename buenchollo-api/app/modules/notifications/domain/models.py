import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base

import app.modules.alerts.domain.models  # noqa: F401
import app.modules.deals.domain.models  # noqa: F401


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str | None] = mapped_column(String, nullable=True)
    link_url: Mapped[str | None] = mapped_column(String, nullable=True)
    deal_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("deals.id", ondelete="CASCADE"), nullable=True
    )
    alert_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    deal = relationship("Deal")
    alert = relationship("Alert")
