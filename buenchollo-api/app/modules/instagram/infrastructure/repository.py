from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.instagram.domain.models import POST_PENDING, InstagramAccount, InstagramPost


class InstagramRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Cola ────────────────────────────────────────────────────────────────

    async def add_post(self, post: InstagramPost) -> InstagramPost:
        self.session.add(post)
        await self.session.flush()
        return post

    async def pending_ids(self, limit: int = 10) -> list[str]:
        rows = await self.session.execute(
            select(InstagramPost.id)
            .where(InstagramPost.status == POST_PENDING)
            .order_by(InstagramPost.created_at)
            .limit(limit)
        )
        return [r[0] for r in rows]

    async def lock_pending(self, post_id: str) -> InstagramPost | None:
        """Bloquea la publicación (FOR UPDATE SKIP LOCKED) si sigue pendiente."""
        rows = await self.session.execute(
            select(InstagramPost)
            .where(InstagramPost.id == post_id, InstagramPost.status == POST_PENDING)
            .with_for_update(skip_locked=True)
        )
        return rows.scalar_one_or_none()

    async def pending_image(self, post_id: str, created_after: datetime) -> bytes | None:
        rows = await self.session.execute(
            select(InstagramPost.image).where(
                InstagramPost.id == post_id,
                InstagramPost.status == POST_PENDING,
                InstagramPost.created_at >= created_after,
            )
        )
        return rows.scalar_one_or_none()

    async def counts(self) -> dict[str, int]:
        rows = await self.session.execute(
            select(InstagramPost.status, func.count()).group_by(InstagramPost.status)
        )
        return {status: count for status, count in rows}

    async def recent(self, limit: int = 10) -> list[InstagramPost]:
        rows = await self.session.execute(
            select(InstagramPost).order_by(InstagramPost.created_at.desc()).limit(limit)
        )
        return list(rows.scalars())

    # ── Cuenta ──────────────────────────────────────────────────────────────

    async def account(self, *, for_update: bool = False) -> InstagramAccount | None:
        query = select(InstagramAccount).where(InstagramAccount.id == 1)
        if for_update:
            query = query.with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()

    async def save_account(self, account: InstagramAccount) -> InstagramAccount:
        self.session.add(account)
        await self.session.flush()
        return account
