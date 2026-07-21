from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.modules.deals.application.deal_service import DealService
from app.modules.scheduled_deals.domain.exceptions import (
    InvalidSchedule,
    ScheduledDealNotEditable,
    ScheduledDealNotFound,
)
from app.modules.scheduled_deals.domain.models import ScheduledDeal, ScheduledDealStatus
from app.modules.scheduled_deals.infrastructure.repository import ScheduledDealRepository
from app.modules.telegram.application.post_generator import TelegramPostGenerator


class ScheduleService:
    PUBLICATION_TIMEZONE = ZoneInfo("Europe/Madrid")
    PUBLICATION_HOURS = range(8, 23, 2)

    def __init__(self, repo: ScheduledDealRepository, deal_service: DealService):
        self.repo = repo
        self.deal_service = deal_service

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _validate_future(self, value: datetime) -> datetime:
        scheduled_at = self._as_utc(value)
        if scheduled_at <= datetime.now(timezone.utc):
            raise InvalidSchedule("La fecha programada debe estar en el futuro")
        if scheduled_at.minute % 5 != 0 or scheduled_at.second != 0 or scheduled_at.microsecond != 0:
            raise InvalidSchedule("La fecha programada debe ajustarse a intervalos de 5 minutos")
        return scheduled_at

    def _validate_before_expiry(
        self, scheduled_at: datetime, expires_at: datetime | None
    ) -> None:
        if expires_at and scheduled_at >= self._as_utc(expires_at):
            raise InvalidSchedule(
                "La fecha programada debe ser anterior a la caducidad del chollo"
            )

    @staticmethod
    def _telegram_text(data: dict) -> str:
        if data.get("telegram_text"):
            return data["telegram_text"]
        return TelegramPostGenerator().generate_text(
            title=data["title"],
            current_price=float(data["offer_price"]),
            previous_price=data.get("regular_price"),
            discount_pct=data.get("discount_percentage"),
            description=data.get("short_description") or data.get("description_web"),
            affiliate_url=data["affiliate_url"],
            expires_at=data.get("expires_at").isoformat() if data.get("expires_at") else None,
        )

    async def create(self, data: dict, user_id: str) -> ScheduledDeal:
        data = dict(data)
        data["scheduled_at"] = self._validate_future(data["scheduled_at"])
        self._validate_before_expiry(data["scheduled_at"], data.get("expires_at"))
        data["telegram_text"] = self._telegram_text(data)

        deal_data = {
            "title": data["title"],
            "slug": data.get("slug"),
            "short_description": data.get("short_description"),
            "description": data.get("description_web"),
            "image_url": data.get("image_url"),
            "images": data.get("images", []),
            "current_price": data["offer_price"],
            "previous_price": data.get("regular_price"),
            "discount_percentage": data.get("discount_percentage", 0),
            "shipping_info": data.get("shipping_info"),
            "affiliate_url": data["affiliate_url"],
            "store_id": data.get("store_id"),
            "category_id": data["category_id"],
            "subcategory_id": data.get("subcategory_id"),
            "brand": data.get("brand"),
            "status": "scheduled",
            "expires_at": data.get("expires_at"),
            "scheduled_for": data["scheduled_at"],
            "source": data.get("source", "manual"),
            "external_id": data["asin"],
            "show_keepa_chart": data.get("show_keepa_chart", False),
        }
        deal = await self.deal_service.create_deal(deal_data, user_id)
        scheduled = ScheduledDeal(
            deal=deal,
            deal_id=deal.id,
            asin=data["asin"],
            title=data["title"],
            description_web=data.get("description_web", ""),
            telegram_text=data["telegram_text"],
            telegram_channel_id=data.get("telegram_channel_id"),
            offer_price=data["offer_price"],
            regular_price=data.get("regular_price"),
            discount_percentage=data.get("discount_percentage", 0),
            image_url=data.get("image_url"),
            affiliate_url=data["affiliate_url"],
            store_name=data.get("store_name", "Amazon"),
            category_id=data["category_id"],
            scheduled_at=data["scheduled_at"],
        )
        return await self.repo.create(scheduled)

    async def get_by_deal_id(self, deal_id: str) -> ScheduledDeal:
        scheduled = await self.repo.get_by_deal_id(deal_id)
        if not scheduled:
            raise ScheduledDealNotFound(deal_id)
        return scheduled

    @classmethod
    def calculate_next_slot(
        cls, latest_scheduled_at: datetime | None, now: datetime | None = None
    ) -> datetime:
        current = cls._as_utc(now or datetime.now(timezone.utc))
        reference = current + timedelta(minutes=10)
        if latest_scheduled_at:
            reference = max(reference, cls._as_utc(latest_scheduled_at))

        local_reference = reference.astimezone(cls.PUBLICATION_TIMEZONE)
        for hour in cls.PUBLICATION_HOURS:
            candidate = datetime.combine(
                local_reference.date(), time(hour=hour), cls.PUBLICATION_TIMEZONE
            )
            if candidate > local_reference:
                return candidate.astimezone(timezone.utc)

        next_day = local_reference.date() + timedelta(days=1)
        return datetime.combine(
            next_day, time(hour=cls.PUBLICATION_HOURS.start), cls.PUBLICATION_TIMEZONE
        ).astimezone(timezone.utc)

    async def get_next_slot(self) -> datetime:
        latest = await self.repo.get_latest_pending_scheduled_at()
        return self.calculate_next_slot(latest)

    async def update(self, scheduled_id: str, changes: dict) -> ScheduledDeal:
        scheduled = await self.repo.get_by_id(scheduled_id)
        if not scheduled:
            raise ScheduledDealNotFound(scheduled_id)
        if scheduled.status != ScheduledDealStatus.SCHEDULED:
            raise ScheduledDealNotEditable()

        changes = dict(changes)
        if "scheduled_at" in changes:
            changes["scheduled_at"] = self._validate_future(changes["scheduled_at"])

        candidate_scheduled_at = changes.get("scheduled_at", scheduled.scheduled_at)
        candidate_expires_at = changes.get("expires_at", scheduled.deal.expires_at)
        self._validate_before_expiry(candidate_scheduled_at, candidate_expires_at)

        schedule_fields = {
            "asin",
            "title",
            "description_web",
            "telegram_text",
            "telegram_channel_id",
            "offer_price",
            "regular_price",
            "discount_percentage",
            "image_url",
            "affiliate_url",
            "store_name",
            "category_id",
            "scheduled_at",
        }
        for field in schedule_fields & changes.keys():
            setattr(scheduled, field, changes[field])

        deal_changes = {}
        mapping = {
            "asin": "external_id",
            "title": "title",
            "description_web": "description",
            "short_description": "short_description",
            "offer_price": "current_price",
            "regular_price": "previous_price",
            "discount_percentage": "discount_percentage",
            "image_url": "image_url",
            "images": "images",
            "affiliate_url": "affiliate_url",
            "store_id": "store_id",
            "category_id": "category_id",
            "subcategory_id": "subcategory_id",
            "brand": "brand",
            "shipping_info": "shipping_info",
            "expires_at": "expires_at",
            "scheduled_at": "scheduled_for",
            "show_keepa_chart": "show_keepa_chart",
        }
        for source, target in mapping.items():
            if source in changes:
                deal_changes[target] = changes[source]
        if deal_changes:
            await self.deal_service.update_deal(scheduled.deal_id, deal_changes)
        return await self.repo.update(scheduled)

    async def reschedule(self, scheduled_id: str, scheduled_at: datetime) -> ScheduledDeal:
        return await self.update(scheduled_id, {"scheduled_at": scheduled_at})

    async def delete(self, scheduled_id: str) -> None:
        scheduled = await self.repo.get_by_id(scheduled_id)
        if not scheduled:
            raise ScheduledDealNotFound(scheduled_id)
        if scheduled.status != ScheduledDealStatus.SCHEDULED:
            raise ScheduledDealNotEditable()
        await self.deal_service.update_deal(
            scheduled.deal_id, {"status": "draft", "scheduled_for": None}
        )
        await self.repo.delete(scheduled)
