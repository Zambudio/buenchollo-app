from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.facebook.domain.models import POST_PENDING, FacebookPost


class FacebookRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_post(self, post: FacebookPost) -> FacebookPost:
        self.session.add(post)
        await self.session.flush()
        return post

    async def pending_ids(self, limit: int = 10) -> list[str]:
        rows = await self.session.execute(
            select(FacebookPost.id)
            .where(FacebookPost.status == POST_PENDING)
            .order_by(FacebookPost.created_at)
            .limit(limit)
        )
        return [r[0] for r in rows]

    async def lock_pending(self, post_id: str) -> FacebookPost | None:
        """Bloquea la publicación (FOR UPDATE SKIP LOCKED) si sigue pendiente."""
        rows = await self.session.execute(
            select(FacebookPost)
            .where(FacebookPost.id == post_id, FacebookPost.status == POST_PENDING)
            .with_for_update(skip_locked=True)
        )
        return rows.scalar_one_or_none()

    async def counts(self) -> dict[str, int]:
        rows = await self.session.execute(select(FacebookPost.status, func.count()).group_by(FacebookPost.status))
        return {status: count for status, count in rows}

    async def recent(self, limit: int = 10) -> list[FacebookPost]:
        rows = await self.session.execute(select(FacebookPost).order_by(FacebookPost.created_at.desc()).limit(limit))
        return list(rows.scalars())
