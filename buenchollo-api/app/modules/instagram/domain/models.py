"""Instagram: cola de publicaciones del feed y cuenta conectada.

Cada chollo que sale en el canal principal de Telegram deja aquí su versión
para Instagram (texto adaptado y la misma imagen, en JPEG). Un job del
scheduler la publica con la API oficial (ver `application/publisher.py`), así
que Telegram nunca espera a Instagram ni falla por él.
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


class InstagramPost(Base):
    __tablename__ = "instagram_posts"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'published', 'error')", name="ck_instagram_posts_status"),
        Index("ix_instagram_posts_status_created", "status", "created_at"),
    )

    # Aleatorio (uuid4): también es la parte secreta de la URL de la imagen.
    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    deal_id: Mapped[str | None] = mapped_column(
        ForeignKey("deals.id", ondelete="SET NULL"), type_=Uuid(as_uuid=False), nullable=True
    )
    caption: Mapped[str] = mapped_column(Text, nullable=False)
    # JPEG que Instagram descarga; se borra al publicar.
    image: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=POST_PENDING)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    container_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    media_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc)
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InstagramAccount(Base):
    """Una sola fila (id = 1): el token vigente, que el job renueva cada semana
    (caduca a los 60 días). El de `INSTAGRAM_ACCESS_TOKEN` solo siembra la
    tabla; si se cambia en el .env, `seed_hash` lo detecta y se usa el nuevo."""

    __tablename__ = "instagram_account"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    seed_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    refreshed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Último problema con el token y cuándo se avisó al canal Admin (como mucho
    # un aviso cada 12 h, el job corre cada 2 min).
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    alerted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
