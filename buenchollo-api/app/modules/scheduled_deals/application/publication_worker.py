import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol

from app.core.config import Settings
from app.core.jobs import job_session
from app.modules.deals.infrastructure.repository import DealRepository
from app.modules.telegram.application.publications import PublicationRecorder
from app.modules.telegram.infrastructure.publication_repository import TelegramPublicationRepository
from app.modules.products.domain.entities import ProductPreview
from app.modules.products.infrastructure.amazon_client import AmazonProductClient
from app.modules.scheduled_deals.domain.models import ScheduledDeal, ScheduledDealStatus
from app.modules.scheduled_deals.infrastructure.repository import ScheduledDealRepository
from app.modules.telegram.application.deal_photo import card_data, render_card, send_deal_post, store_name_of
from app.modules.telegram.application.post_generator import TelegramPostGenerator
from app.modules.telegram.application.whatsapp_copy import send_whatsapp_copy
from app.modules.telegram.infrastructure.telegram_bot import TelegramBot
from app.modules.instagram.application.queue import is_main_channel, queue_instagram_post

logger = logging.getLogger(__name__)


class ProductVerifier(Protocol):
    def get_product_preview(self, asin: str) -> ProductPreview | None: ...


class PublicationBot(Protocol):
    def send_preformatted(
        self, text: str, entities: list[dict], image_url: str | None = None,
        chat_id: str | None = None,
    ) -> bool: ...

    def send_admin_notification(self, text: str, chat_id: str | None = None) -> bool: ...

    # Tarjeta de oferta (deal_photo.py). Un bot sin ellas publica la foto original.
    def download_image(self, url: str) -> bytes | None: ...

    def send_photo_bytes(
        self, content: bytes, chat_id: str | None = None, caption: str = "",
        entities: list[dict] | None = None,
    ) -> bool: ...


class ScheduledPublicationWorker:
    def __init__(
        self,
        session,
        repo: ScheduledDealRepository,
        product_verifier: ProductVerifier,
        bot: PublicationBot,
        main_channel_id: str,
        admin_chat_id: str,
        publications=None,
        settings: Settings | None = None,
    ):
        self.session = session
        self.repo = repo
        self.product_verifier = product_verifier
        self.bot = bot
        self.main_channel_id = main_channel_id
        self.admin_chat_id = admin_chat_id
        self.generator = TelegramPostGenerator()
        # Registro de lo enviado (telegram_publications); opcional en tests.
        self.publications = publications
        # Para la cola de Instagram (None en tests que no la usan).
        self.settings = settings
        # Tarjeta de oferta y texto del último post enviado (los reutilizan el
        # registro y la copia de WhatsApp).
        self._card: bytes | None = None
        self._sent_text: str | None = None

    async def process_due(self, now: datetime | None = None) -> int:
        """Una transacción por programación (como en scheduled_tasks, finding 8):
        lo ya publicado en Telegram queda confirmado aunque la BD falle en una
        programación posterior. Con un único commit final, ese rollback la
        devolvía a «pendiente» y se reenviaba en el siguiente tick.

        Cada una se bloquea con FOR UPDATE SKIP LOCKED en su propia transacción,
        de modo que el commit de una no libera el bloqueo de las demás."""
        current_time = now or datetime.now(timezone.utc)
        pending_ids = await self.repo.get_pending_ids_until(current_time + timedelta(minutes=5))
        processed = 0
        for scheduled_id in pending_ids:
            try:
                scheduled = await self.repo.lock_pending(scheduled_id)
                if scheduled is not None:
                    processed += 1
                    await self._process_or_mark_error(scheduled, current_time)
                await self.session.commit()
            except Exception:
                logger.exception("Error de BD procesando la programacion %s", scheduled_id)
                await self.session.rollback()
        return processed

    async def _process_or_mark_error(self, scheduled: ScheduledDeal, now: datetime) -> None:
        try:
            await self._process_one(scheduled, now)
        except Exception as exc:
            logger.exception("Error publicando programacion %s", scheduled.id)
            scheduled.status = ScheduledDealStatus.ERROR
            scheduled.cancellation_reason = str(exc)[:500]
            await self.repo.update(scheduled)
            self._notify_admin(
                f"⚠️ Error al publicar automáticamente: {scheduled.title}. {str(exc)[:250]}"
            )

    async def _process_one(self, scheduled: ScheduledDeal, now: datetime) -> None:
        # Una ficha web incompleta sigue siendo una programación válida de Telegram.
        # Sin ASIN/precio verificables se conserva el texto aprobado por el admin.
        if not scheduled.asin or scheduled.offer_price <= 0:
            if scheduled.web_ready:
                raise RuntimeError("Programación web sin ASIN o precio válido")
            if scheduled.scheduled_at > now:
                return
            await self._send_telegram_only(scheduled)
            return

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

        if current_price != old_price and scheduled.web_ready:
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

        if not scheduled.web_ready:
            await self._send_telegram_only(scheduled)
            return

        published_to_telegram = await self._send_post(scheduled, destination_channel_id)
        if not published_to_telegram:
            last_err = getattr(self.bot, "last_error", None)
            detail = f": {last_err}" if last_err else ""
            raise RuntimeError(f"Telegram rechazo la publicacion{detail}")

        scheduled.deal.current_price = current_price
        scheduled.deal.discount_percentage = scheduled.discount_percentage
        scheduled.deal.savings_amount = self._savings(current_price, scheduled.regular_price)
        scheduled.deal.shipping_info = product.shipping_type or scheduled.deal.shipping_info
        scheduled.deal.status = "active"
        scheduled.deal.published_at = now
        # Después de actualizar el deal: el registro guarda el precio publicado.
        await self._record(scheduled, destination_channel_id)
        await self._send_whatsapp_copy(scheduled)
        await self._queue_instagram(scheduled, destination_channel_id)
        scheduled.status = ScheduledDealStatus.PUBLISHED
        scheduled.cancellation_reason = None
        await self.repo.update(scheduled)

    async def _send_telegram_only(self, scheduled: ScheduledDeal) -> None:
        destination = scheduled.telegram_channel_id or self.main_channel_id
        if not destination:
            raise RuntimeError("TELEGRAM_MAIN_CHANNEL_ID no configurado")
        if not await self._send_post(scheduled, destination):
            raise RuntimeError("Telegram rechazo la publicacion")
        await self._record(scheduled, destination)
        await self._send_whatsapp_copy(scheduled)
        await self._queue_instagram(scheduled, destination)
        scheduled.status = ScheduledDealStatus.PUBLISHED
        scheduled.cancellation_reason = None
        await self.repo.update(scheduled)

    async def _send_post(self, scheduled: ScheduledDeal, chat_id: str) -> bool:
        """Publica con la tarjeta de oferta (precio de la programación, ya
        verificado) o, si no se puede, con la foto original. La tarjeta se guarda
        para la copia de WhatsApp. En un hilo: descarga, Pillow y HTTP bloquean."""
        deal = getattr(scheduled, "deal", None)
        store = store_name_of(deal)
        data = card_data(scheduled.offer_price, scheduled.regular_price, store, scheduled.discount_percentage)
        self._card = await asyncio.to_thread(render_card, self.bot, scheduled.image_url, data)
        self._sent_text = await asyncio.to_thread(
            send_deal_post,
            self.bot,
            text=scheduled.telegram_text,
            entities_for=lambda text: self.generator.build_entities(text, store_name=store),
            image_url=scheduled.image_url,
            chat_id=chat_id,
            card=self._card,
            data=data,
        )
        return self._sent_text is not None

    async def _send_whatsapp_copy(self, scheduled: ScheduledDeal) -> None:
        """Después de registrar: el segundo envío pisa `bot.last_message_id`.
        En un hilo: son hasta tres peticiones HTTP bloqueantes."""
        await asyncio.to_thread(
            send_whatsapp_copy,
            self.bot,
            chat_id=self.admin_chat_id,
            telegram_text=self._sent_text or scheduled.telegram_text,
            image_url=scheduled.image_url,
            image_bytes=self._card,
        )

    async def _queue_instagram(self, scheduled: ScheduledDeal, channel_id: str) -> None:
        """Encola la versión de Instagram si salió en el canal principal. Nunca lanza."""
        if self.settings is None or not is_main_channel(channel_id, self.settings):
            return
        await queue_instagram_post(
            self.session,
            self.settings,
            deal_id=getattr(scheduled, "deal_id", None),
            telegram_text=self._sent_text or scheduled.telegram_text,
            card=self._card,
            image_url=scheduled.image_url,
            download=getattr(self.bot, "download_image", None),
        )

    async def _record(self, scheduled: ScheduledDeal, channel_id: str) -> None:
        if self.publications is None:
            return
        try:
            await self._record_unsafe(scheduled, channel_id)
        except Exception:
            # Ya está publicado: un fallo del registro no puede marcarlo como
            # error ni hacer que se vuelva a publicar.
            logger.exception("No se pudo registrar la publicación de %s", scheduled.id)

    async def _record_unsafe(self, scheduled: ScheduledDeal, channel_id: str) -> None:
        await self.publications.record(
            deal_id=getattr(scheduled, "deal_id", None),
            channel_id=channel_id,
            text=self._sent_text or scheduled.telegram_text,
            image_url=scheduled.image_url,
            message_id=getattr(self.bot, "last_message_id", None),
        )

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
    async with job_session(settings) as session:
        try:
            worker = ScheduledPublicationWorker(
                session,
                ScheduledDealRepository(session),
                AmazonProductClient(settings),
                TelegramBot(settings.telegram_bot_token),
                settings.telegram_main_channel_id,
                settings.telegram_admin_channel_id,
                publications=PublicationRecorder(
                    TelegramPublicationRepository(session), DealRepository(session), settings, "scheduled"
                ),
                settings=settings,
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


def run_due_scheduled_publications(settings: Settings) -> int:
    return asyncio.run(_run(settings))
