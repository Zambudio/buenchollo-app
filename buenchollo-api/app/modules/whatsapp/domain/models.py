"""WhatsApp: cola de publicaciones del Canal de WhatsApp.

Cada chollo que sale en un canal de Telegram de `WHATSAPP_CHANNELS` deja aquí
su versión para WhatsApp (texto y la misma tarjeta, en JPEG). Un job del
scheduler la publica a través de la pasarela (`whatsapp-gateway`), con un ritmo
mínimo entre publicaciones y un tope diario (ver `application/publisher.py`).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, LargeBinary, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base

import app.modules.deals.domain.models  # noqa: F401  (FK a deals)

POST_PENDING = "pending"
POST_PUBLISHED = "published"
POST_ERROR = "error"


class WhatsAppPost(Base):
    __tablename__ = "whatsapp_posts"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'published', 'error')", name="ck_whatsapp_posts_status"),
        Index("ix_whatsapp_posts_status_created", "status", "created_at"),
        Index("ix_whatsapp_posts_published_at", "published_at"),
        Index("ix_whatsapp_posts_deal_id", "deal_id"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    deal_id: Mapped[str | None] = mapped_column(
        ForeignKey("deals.id", ondelete="SET NULL"), type_=Uuid(as_uuid=False), nullable=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Tarjeta de oferta (JPEG); None → solo texto. Se borra al publicar.
    image: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=POST_PENDING)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc)
    )
    # No sale antes de esta hora (un margen aleatorio de segundos tras Telegram).
    not_before: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
