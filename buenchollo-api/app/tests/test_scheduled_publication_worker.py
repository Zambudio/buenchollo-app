from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.modules.products.domain.entities import ProductPreview
from app.modules.scheduled_deals.application.publication_worker import ScheduledPublicationWorker
from app.modules.scheduled_deals.domain.models import ScheduledDealStatus


class FakeRepository:
    def __init__(self, scheduled):
        self.scheduled = scheduled

    async def get_pending_until_for_update(self, horizon):
        return [self.scheduled]

    async def update(self, scheduled):
        return scheduled


class FakeVerifier:
    def __init__(self, product):
        self.product = product

    def get_product_preview(self, asin):
        return self.product


class FakeBot:
    def __init__(self, publish_ok=True):
        self.publish_ok = publish_ok
        self.posts = []
        self.admin_messages = []

    def send_preformatted(self, **payload):
        self.posts.append(payload)
        return self.publish_ok

    def send_admin_notification(self, text, chat_id=None):
        self.admin_messages.append((text, chat_id))
        return True


def scheduled_deal():
    deal = SimpleNamespace(
        current_price=Decimal("100.00"),
        discount_percentage=20,
        savings_amount=Decimal("20.00"),
        shipping_info=None,
        short_description="Descripción",
        expires_at=None,
        status="scheduled",
        published_at=None,
    )
    return SimpleNamespace(
        id="schedule-id",
        asin="B0D9WH9WLD",
        title="Producto",
        offer_price=Decimal("100.00"),
        regular_price=Decimal("125.00"),
        discount_percentage=20,
        telegram_text="🍄 Producto\n\n💶 Precio: 100.00 €",
        telegram_channel_id="-100-destination",
        description_web="Descripción web",
        affiliate_url="https://amazon.es/dp/B0D9WH9WLD",
        image_url="https://images.test/product.jpg",
        scheduled_at=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        status=ScheduledDealStatus.SCHEDULED,
        cancellation_reason=None,
        deal=deal,
    )


def worker_for(scheduled, product, bot=None):
    bot = bot or FakeBot()
    worker = ScheduledPublicationWorker(
        FakeRepository(scheduled),
        FakeVerifier(product),
        bot,
        main_channel_id="-100-main",
        admin_chat_id="123-admin",
    )
    return worker, bot


@pytest.mark.asyncio
async def test_publica_web_y_telegram_si_precio_y_stock_se_mantienen():
    scheduled = scheduled_deal()
    product = ProductPreview(current_price=100.0, in_stock=True, shipping_type="Prime")
    worker, bot = worker_for(scheduled, product)

    processed = await worker.process_due(datetime.now(timezone.utc))

    assert processed == 1
    assert scheduled.status == ScheduledDealStatus.PUBLISHED
    assert scheduled.deal.status == "active"
    assert scheduled.deal.shipping_info == "Prime"
    assert len(bot.posts) == 1
    assert bot.posts[0]["chat_id"] == "-100-destination"
    assert bot.admin_messages == []


@pytest.mark.asyncio
async def test_usa_canal_principal_para_programaciones_anteriores_sin_destino():
    scheduled = scheduled_deal()
    scheduled.telegram_channel_id = None
    product = ProductPreview(current_price=100.0, in_stock=True)
    worker, bot = worker_for(scheduled, product)

    await worker.process_due(datetime.now(timezone.utc))

    assert bot.posts[0]["chat_id"] == "-100-main"


@pytest.mark.asyncio
async def test_actualiza_precio_descuento_y_texto_si_variacion_es_hasta_diez_por_ciento():
    scheduled = scheduled_deal()
    product = ProductPreview(current_price=108.0, in_stock=True)
    worker, bot = worker_for(scheduled, product)

    await worker.process_due(datetime.now(timezone.utc))

    assert scheduled.status == ScheduledDealStatus.PUBLISHED
    assert scheduled.offer_price == Decimal("108.00")
    assert scheduled.discount_percentage == 14
    assert "108.00" in scheduled.telegram_text
    assert len(bot.posts) == 1


@pytest.mark.asyncio
async def test_cancela_y_avisa_si_precio_supera_diez_por_ciento():
    scheduled = scheduled_deal()
    product = ProductPreview(current_price=111.0, in_stock=True)
    worker, bot = worker_for(scheduled, product)

    await worker.process_due(datetime.now(timezone.utc))

    assert scheduled.status == ScheduledDealStatus.CANCELLED_PRICE
    assert scheduled.deal.status == "scheduled"
    assert bot.posts == []
    assert "ha subido de 100.00€ a 111.00€" in bot.admin_messages[0][0]


@pytest.mark.asyncio
async def test_cancela_y_avisa_si_no_hay_stock():
    scheduled = scheduled_deal()
    product = ProductPreview(current_price=100.0, in_stock=False)
    worker, bot = worker_for(scheduled, product)

    await worker.process_due(datetime.now(timezone.utc))

    assert scheduled.status == ScheduledDealStatus.CANCELLED_STOCK
    assert scheduled.deal.status == "scheduled"
    assert bot.posts == []
    assert "sin stock" in bot.admin_messages[0][0]


@pytest.mark.asyncio
async def test_precomprueba_cinco_minutos_antes_sin_publicar():
    now = datetime(2026, 7, 20, 10, 0, tzinfo=timezone.utc)
    scheduled = scheduled_deal()
    scheduled.scheduled_at = now.replace(minute=5)
    product = ProductPreview(current_price=98.0, in_stock=True)
    worker, bot = worker_for(scheduled, product)

    await worker.process_due(now)

    assert scheduled.status == ScheduledDealStatus.SCHEDULED
    assert scheduled.offer_price == Decimal("98.00")
    assert scheduled.deal.status == "scheduled"
    assert bot.posts == []
