from datetime import datetime

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.deals.domain.models import Deal
from app.modules.stores.domain.models import Store
from app.modules.submissions.domain.models import PENDING, DealSubmission

LIVE_STATUSES = ("active", "scheduled", "draft")


def _normalize_host(value: str | None) -> str:
    host = (value or "").strip().lower()
    for prefix in ("https://", "http://"):
        host = host.removeprefix(prefix)
    return host.split("/", 1)[0].removeprefix("www.")


class SubmissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _match(asin_col, url_col, asin: str | None, canonical_url: str):
        condition = url_col == canonical_url
        if asin:
            condition = condition | (asin_col == asin)
        return condition

    async def find_live_deal(self, asin: str | None, canonical_url: str) -> Deal | None:
        stmt = (
            select(Deal)
            .where(
                Deal.status.in_(LIVE_STATUSES),
                self._match(Deal.external_id, Deal.canonical_url, asin, canonical_url),
            )
            .order_by(case((Deal.status == "active", 0), else_=1), Deal.published_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def find_expired_deal(self, asin: str | None, canonical_url: str) -> Deal | None:
        stmt = (
            select(Deal)
            .where(
                Deal.status == "expired",
                self._match(Deal.external_id, Deal.canonical_url, asin, canonical_url),
            )
            .order_by(Deal.published_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def find_pending(self, asin: str | None, canonical_url: str) -> DealSubmission | None:
        stmt = (
            select(DealSubmission)
            .where(
                DealSubmission.status == PENDING,
                self._match(DealSubmission.asin, DealSubmission.canonical_url, asin, canonical_url),
            )
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def find_store_by_host(self, host: str) -> Store | None:
        target = _normalize_host(host)
        if not target:
            return None
        result = await self.session.execute(
            select(Store).where(Store.is_active.is_(True), Store.domain.is_not(None))
        )
        for store in result.scalars():
            if _normalize_host(store.domain) == target:
                return store
        return None

    async def count_pending_by_user(self, user_id: str) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(DealSubmission)
            .where(DealSubmission.user_id == user_id, DealSubmission.status == PENDING)
        )
        return int(result.scalar_one())

    async def count_since(self, user_id: str, since: datetime) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(DealSubmission)
            .where(DealSubmission.user_id == user_id, DealSubmission.created_at >= since)
        )
        return int(result.scalar_one())

    async def add(self, sub: DealSubmission) -> DealSubmission:
        self.session.add(sub)
        await self.session.flush()
        return sub

    async def get(self, id: str) -> DealSubmission | None:
        stmt = (
            select(DealSubmission)
            .where(DealSubmission.id == id)
            .options(
                selectinload(DealSubmission.user),
                selectinload(DealSubmission.category),
                selectinload(DealSubmission.subcategory),
                selectinload(DealSubmission.store),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_by_user(self, user_id: str, limit: int, offset: int) -> list[DealSubmission]:
        stmt = (
            select(DealSubmission)
            .where(DealSubmission.user_id == user_id)
            .order_by(DealSubmission.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_by_status(self, status: str, limit: int, offset: int) -> list[DealSubmission]:
        stmt = (
            select(DealSubmission)
            .where(DealSubmission.status == status)
            .options(selectinload(DealSubmission.user))
            .order_by(DealSubmission.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_by_status(self, status: str) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(DealSubmission).where(DealSubmission.status == status)
        )
        return int(result.scalar_one())

    async def claim_pending(self, id: str, new_status: str) -> bool:
        result = await self.session.execute(
            update(DealSubmission)
            .where(DealSubmission.id == id, DealSubmission.status == PENDING)
            .values(status=new_status)
        )
        return result.rowcount == 1
