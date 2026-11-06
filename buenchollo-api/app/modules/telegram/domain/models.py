"""Publicaciones enviadas a Telegram: el texto exacto, la imagen, el canal y los
precios del chollo en ese momento. Sirven para reenviar la publicación con el
precio corregido cuando el chollo vuelve a estar en oferta (catálogo permanente)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base

# FK a deals y profiles: registrar sus tablas antes de resolver las relaciones.
import app.modules.deals.domain.models  # noqa: F401
import app.modules.users.domain.models  # noqa: F401


class TelegramPublication(Base):
    __tablename__ = "telegram_publications"
    __table_args__ = (Index("ix_telegram_publications_deal_sent", "deal_id", "sent_at"),)

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    deal_id: Mapped[str | None] = mapped_column(
        ForeignKey("deals.id", ondelete="CASCADE"), type_=Uuid(as_uuid=False), nullable=True
    )
    channel_id: Mapped[str] = mapped_column(String(100), nullable=False)
    channel_kind: Mapped[str] = mapped_column(String(16), nullable=False)  # main | admin | other
    source: Mapped[str] = mapped_column(String(16), nullable=False)  # panel | scheduled
    text: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    previous_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    discount_percentage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sent_by: Mapped[str | None] = mapped_column(
        ForeignKey("profiles.user_id", ondelete="SET NULL"), type_=Uuid(as_uuid=False), nullable=True
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc)
    )
