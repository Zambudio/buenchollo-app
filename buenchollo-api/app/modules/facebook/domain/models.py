"""Facebook: cola de publicaciones de la página.

Cada chollo que sale en los canales de Telegram de `FACEBOOK_CHANNELS` deja
aquí su versión para Facebook (texto adaptado y la misma imagen, en JPEG). Un
job del scheduler la publica con la Graph API (ver `application/publisher.py`),
así que Telegram nunca espera a Facebook ni falla por él.
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


class FacebookPost(Base):
    __tablename__ = "facebook_posts"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'published', 'error')", name="ck_facebook_posts_status"),
        Index("ix_facebook_posts_status_created", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    deal_id: Mapped[str | None] = mapped_column(
        ForeignKey("deals.id", ondelete="SET NULL"), type_=Uuid(as_uuid=False), nullable=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    # JPEG que se sube a Facebook; se borra al publicar o al descartarse.
    image: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=POST_PENDING)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    post_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc)
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
