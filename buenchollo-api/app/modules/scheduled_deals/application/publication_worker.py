import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.modules.products.domain.entities import ProductPreview
from app.modules.products.infrastructure.amazon_client import AmazonProductClient
from app.modules.scheduled_deals.domain.models import ScheduledDeal, ScheduledDealStatus
from app.modules.scheduled_deals.infrastructure.repository import ScheduledDealRepository
from app.modules.telegram.application.post_generator import TelegramPostGenerator
from app.modules.telegram.infrastructure.telegram_bot import TelegramBot

logger = logging.getLogger(__name__)


class ProductVerifier(Protocol):
    def get_product_preview(self, asin: str) -> ProductPreview | None: ...


class PublicationBot(Protocol):
    def send_preformatted(
        self, text: str, entities: list[dict], image_url: str | None = None,
        chat_id: str | None = None,
    ) -> bool: ...

    def send_admin_notification(self, text: str, chat_id: str | None = None) -> bool: ...


class ScheduledPublicationWorker:
    def __init__(
        self,
        repo: ScheduledDealRepository,
        product_verifier: ProductVerifier,
        bot: PublicationBot,
        main_channel_id: str,
        admin_chat_id: str,
    ):
        self.repo = repo
        self.product_verifier = product_verifier
        self.bot = bot
        self.main_channel_id = main_channel_id
        self.admin_chat_id = admin_chat_id
        self.generator = TelegramPostGenerator()

    async def process_due(self, now: datetime | None = None) -> int:
        current_time = now or datetime.now(timezone.utc)
        pending = await self.repo.get_pending_until_for_update(
            current_time + timedelta(minutes=5)
        )
        for scheduled in pending:
            try:
                await self._process_one(scheduled, current_time)
            except Exception as exc:
                logger.exception("Error publicando programacion %s", scheduled.id)
                scheduled.status = ScheduledDealStatus.ERROR
                scheduled.cancellation_reason = str(exc)[:500]
                await self.repo.update(scheduled)
                self._notify_admin(
                    f"⚠️ Error al publicar automáticamente: {scheduled.title}. {str(exc)[:250]}"
                )
        return len(pending)

    async def _process_one(self, scheduled: ScheduledDeal, now: datetime) -> None:
        product = self.product_verifier.get_product_preview(scheduled.asin)
        if product is None or not product.in_stock or product.current_price is None:
            scheduled.status = ScheduledDealStatus.CANCELLED_STOCK
            scheduled.cancellation_reason = "Amazon no informa una oferta disponible con stock"
            await self.repo.update(scheduled)
            self._notify_admin(
                f"⚠️ Oferta cancelada automáticamente: {scheduled.title} está sin stock."
            )
            return

        old_price = Decimal(str(scheduled.offer_price))
        current_price = Decimal(str(product.current_price)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        maximum_price = old_price * Decimal("1.10")
        if current_price > maximum_price:
            scheduled.status = ScheduledDealStatus.CANCELLED_PRICE
            scheduled.cancellation_reason = (
                f"Precio subio de {old_price:.2f} EUR a {current_price:.2f} EUR"
            )
            await self.repo.update(scheduled)
            self._notify_admin(
                f"⚠️ Oferta cancelada automáticamente: {scheduled.title} "
                f"ha subido de {old_price:.2f}€ a {current_price:.2f}€."
            )
            return

        destination_channel_id = scheduled.telegram_channel_id or self.main_channel_id
        if not destination_channel_id:
            raise RuntimeError("TELEGRAM_MAIN_CHANNEL_ID no configurado")

        if current_price != old_price:
            scheduled.offer_price = current_price
            scheduled.discount_percentage = self._discount(
                current_price, scheduled.regular_price
            )
            scheduled.telegram_text = self.generator.generate_text(
                title=scheduled.title,
                current_price=float(current_price),
                previous_price=float(scheduled.regular_price) if scheduled.regular_price else None,
                discount_pct=scheduled.discount_percentage,
                description=scheduled.deal.short_description or scheduled.description_web,
                affiliate_url=scheduled.affiliate_url,
                expires_at=scheduled.deal.expires_at.isoformat() if scheduled.deal.expires_at else None,
            )

        if scheduled.scheduled_at > now:
            await self.repo.update(scheduled)
            return

        entities = self.generator.build_entities(scheduled.telegram_text)
        published_to_telegram = self.bot.send_preformatted(
            text=scheduled.telegram_text,
            entities=entities,
            image_url=scheduled.image_url,
            chat_id=destination_channel_id,
        )
        if not published_to_telegram:
            raise RuntimeError("Telegram rechazo la publicacion")

        scheduled.deal.current_price = current_price
        scheduled.deal.discount_percentage = scheduled.discount_percentage
        scheduled.deal.savings_amount = self._savings(current_price, scheduled.regular_price)
        scheduled.deal.shipping_info = product.shipping_type or scheduled.deal.shipping_info
        scheduled.deal.status = "active"
        scheduled.deal.published_at = now
        scheduled.status = ScheduledDealStatus.PUBLISHED
        scheduled.cancellation_reason = None
        await self.repo.update(scheduled)

    @staticmethod
    def _discount(current: Decimal, regular: Decimal | None) -> int:
        if not regular or regular <= current:
            return 0
        return int(((regular - current) / regular * 100).quantize(Decimal("1")))

    @staticmethod
    def _savings(current: Decimal, regular: Decimal | None) -> Decimal | None:
        if not regular or regular <= current:
            return None
        return (regular - current).quantize(Decimal("0.01"))

    def _notify_admin(self, text: str) -> None:
        if self.admin_chat_id:
            self.bot.send_admin_notification(text, chat_id=self.admin_chat_id)


async def _run(settings: Settings) -> int:
    if not settings.database_url:
        logger.error("DATABASE_URL no configurada para el worker de programaciones")
        return 0
    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
        connect_args={"server_settings": {"jit": "off"}, "statement_cache_size": 0},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            try:
                worker = ScheduledPublicationWorker(
                    ScheduledDealRepository(session),
                    AmazonProductClient(settings),
                    TelegramBot(settings.telegram_bot_token),
                    settings.telegram_main_channel_id,
                    settings.telegram_admin_channel_id,
                )
                count = await worker.process_due()
                await session.commit()
                if count:
                    logger.info("Worker de programaciones proceso %d chollo(s)", count)
                return count
            except Exception:
                await session.rollback()
                logger.exception("Fallo global del worker de programaciones")
                return 0
    finally:
        await engine.dispose()


def run_due_scheduled_publications(settings: Settings) -> int:
    return asyncio.run(_run(settings))
