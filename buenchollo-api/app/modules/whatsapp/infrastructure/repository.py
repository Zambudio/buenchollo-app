from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.whatsapp.domain.models import POST_ERROR, POST_PENDING, POST_PUBLISHED, WhatsAppPost


class WhatsAppRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_post(self, post: WhatsAppPost) -> WhatsAppPost:
        self.session.add(post)
        await self.session.flush()
        return post

    async def has_recent_for_deal(self, deal_id: str, since: datetime) -> bool:
        """Ya hay una publicación (pendiente o hecha) de ese chollo desde `since`:
        no se repite si sale en el canal principal y en el Admin."""
        rows = await self.session.execute(
            select(WhatsAppPost.id)
            .where(
                WhatsAppPost.deal_id == deal_id,
                WhatsAppPost.status != POST_ERROR,
                WhatsAppPost.created_at >= since,
            )
            .limit(1)
        )
        return rows.first() is not None

    async def has_recent_text(self, text: str, since: datetime) -> bool:
        """Mismo texto (pendiente o publicado) desde `since`: para lo que no es
        de un chollo concreto, como el resumen semanal."""
        rows = await self.session.execute(
            select(WhatsAppPost.id)
            .where(WhatsAppPost.text == text, WhatsAppPost.status != POST_ERROR, WhatsAppPost.created_at >= since)
            .limit(1)
        )
        return rows.first() is not None

    async def next_due(self, now: datetime) -> WhatsAppPost | None:
        """La pendiente más antigua que ya puede salir, bloqueada (SKIP LOCKED)."""
        rows = await self.session.execute(
            select(WhatsAppPost)
            .where(
                WhatsAppPost.status == POST_PENDING,
                or_(WhatsAppPost.not_before.is_(None), WhatsAppPost.not_before <= now),
            )
            .order_by(WhatsAppPost.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        return rows.scalar_one_or_none()

    async def last_published_at(self) -> datetime | None:
        rows = await self.session.execute(
            select(func.max(WhatsAppPost.published_at)).where(WhatsAppPost.status == POST_PUBLISHED)
        )
        return rows.scalar_one_or_none()

    async def published_since(self, since: datetime) -> int:
        rows = await self.session.execute(
            select(func.count()).where(WhatsAppPost.status == POST_PUBLISHED, WhatsAppPost.published_at >= since)
        )
        return int(rows.scalar_one() or 0)

    async def counts(self) -> dict[str, int]:
        rows = await self.session.execute(select(WhatsAppPost.status, func.count()).group_by(WhatsAppPost.status))
        return {status: count for status, count in rows}

    async def recent(self, limit: int = 10) -> list[WhatsAppPost]:
        rows = await self.session.execute(select(WhatsAppPost).order_by(WhatsAppPost.created_at.desc()).limit(limit))
        return list(rows.scalars())
