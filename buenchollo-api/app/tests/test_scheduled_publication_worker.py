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

    async def get_pending_ids_until(self, horizon):
        return [self.scheduled.id]

    async def lock_pending(self, scheduled_id):
        return self.scheduled

    async def update(self, scheduled):
        return scheduled


class FakeSession:
    async def commit(self):
        pass

    async def rollback(self):
        pass


class FakeVerifier:
    def __init__(self, product):
        self.product = product

    def get_product_preview(self, asin):
        return self.product


class FakeBot:
    def __init__(self, publish_ok=True):
        self.publish_ok = publish_ok
        self.posts = []
        # Versión WhatsApp (texto plano, sin entidades) enviada tras publicar
        self.whatsapp_copies = []
        self.admin_messages = []

    def send_preformatted(self, **payload):
        (self.posts if payload["entities"] else self.whatsapp_copies).append(payload)
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
        web_ready=True,
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
        FakeSession(),
        FakeRepository(scheduled),
        FakeVerifier(product),
        bot,
        main_channel_id="-100-main",
        admin_chat_id="123-admin",
    )
    return worker, bot


@pytest.mark.asyncio
async def test_telegram_only_publishes_without_activating_incomplete_web_deal():
    scheduled = scheduled_deal()
    scheduled.web_ready = False
    scheduled.asin = None
    scheduled.offer_price = Decimal("0")
    scheduled.deal.status = "draft"
    worker, bot = worker_for(scheduled, None)

    await worker.process_due(datetime.now(timezone.utc))

    assert scheduled.status == ScheduledDealStatus.PUBLISHED
    assert scheduled.deal.status == "draft"
    assert len(bot.posts) == 1
    assert [copy["chat_id"] for copy in bot.whatsapp_copies] == ["123-admin"]


@pytest.mark.asyncio
async def test_missing_web_category_still_sends_telegram_after_product_verification():
    scheduled = scheduled_deal()
    scheduled.web_ready = False
    scheduled.deal.status = "draft"
    product = ProductPreview(current_price=100.0, in_stock=True)
    worker, bot = worker_for(scheduled, product)

    await worker.process_due(datetime.now(timezone.utc))

    assert scheduled.status == ScheduledDealStatus.PUBLISHED
    assert scheduled.deal.status == "draft"
    assert len(bot.posts) == 1


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
    assert len(bot.whatsapp_copies) == 1
    whatsapp = bot.whatsapp_copies[0]
    assert whatsapp["chat_id"] == "123-admin"  # nunca al canal público
    assert whatsapp["image_url"] == bot.posts[0]["image_url"]
    assert whatsapp["text"].startswith("🔥 *")
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
    # El texto nuevo no lleva el precio (va en la tarjeta); este bot no envía
    # tarjetas, así que el post sale con la foto original y el precio añadido.
    assert "💶" not in scheduled.telegram_text
    assert len(bot.posts) == 1
    assert "108,00" in bot.posts[0]["text"]


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


class FakePublications:
    def __init__(self):
        self.recorded = []

    async def record(self, **kwargs):
        self.recorded.append(kwargs)


@pytest.mark.asyncio
async def test_registra_la_publicacion_enviada_por_el_programador():
    scheduled = scheduled_deal()
    scheduled.deal_id = "deal-1"
    scheduled.scheduled_at = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    product = ProductPreview(current_price=100.0, in_stock=True)
    publications = FakePublications()
    worker, bot = worker_for(scheduled, product)
    worker.publications = publications

    await worker.process_due(datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc))

    assert scheduled.status == ScheduledDealStatus.PUBLISHED
    [record] = publications.recorded
    assert record["deal_id"] == "deal-1" and record["channel_id"] == "-100-destination"
    assert record["text"] == scheduled.telegram_text and record["image_url"] == scheduled.image_url


@pytest.mark.asyncio
async def test_registra_tambien_la_publicacion_solo_telegram():
    scheduled = scheduled_deal()
    scheduled.deal_id = "deal-2"
    scheduled.web_ready = False
    scheduled.asin = None
    scheduled.offer_price = Decimal("0")
    publications = FakePublications()
    worker, _ = worker_for(scheduled, None)
    worker.publications = publications

    await worker.process_due(datetime.now(timezone.utc))

    assert [r["deal_id"] for r in publications.recorded] == ["deal-2"]


@pytest.mark.asyncio
async def test_un_fallo_al_registrar_no_deshace_la_publicacion_ni_la_repite():
    class BrokenPublications:
        async def record(self, **kwargs):
            raise RuntimeError("BD caída")

    scheduled = scheduled_deal()
    scheduled.deal_id = "deal-1"
    product = ProductPreview(current_price=90.0, in_stock=True)
    worker, bot = worker_for(scheduled, product)
    worker.publications = BrokenPublications()

    await worker.process_due(datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc))

    assert scheduled.status == ScheduledDealStatus.PUBLISHED
    assert len(bot.posts) == 1 and bot.admin_messages == []


@pytest.mark.asyncio
async def test_registra_el_precio_ya_actualizado_del_chollo():
    seen = {}

    class SpyPublications:
        async def record(self, **kwargs):
            seen["deal_price"] = scheduled.deal.current_price

    scheduled = scheduled_deal()
    scheduled.deal_id = "deal-1"
    worker, _ = worker_for(scheduled, ProductPreview(current_price=95.0, in_stock=True))
    worker.publications = SpyPublications()

    await worker.process_due(datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc))

    assert seen["deal_price"] == Decimal("95.00")


class TransactionalStore:
    """Repo y sesión falsos con semántica de transacción: el estado de las
    programaciones solo persiste con commit y rollback vuelve a lo confirmado."""

    def __init__(self, items, fail_update_for=None):
        self.items = {s.id: s for s in items}
        self.committed = {s.id: s.status for s in items}
        self.fail_update_for = fail_update_for
        self.locked_elsewhere = set()

    async def get_pending_ids_until(self, horizon):
        return [i for i, status in self.committed.items() if status == ScheduledDealStatus.SCHEDULED]

    async def lock_pending(self, scheduled_id):
        scheduled = self.items[scheduled_id]
        if scheduled_id in self.locked_elsewhere or scheduled.status != ScheduledDealStatus.SCHEDULED:
            return None
        return scheduled

    async def update(self, scheduled):
        if scheduled.id == self.fail_update_for:
            raise RuntimeError("BD caída")
        return scheduled

    async def commit(self):
        self.committed = {i: s.status for i, s in self.items.items()}

    async def rollback(self):
        for i, status in self.committed.items():
            self.items[i].status = status


def _store_worker(store, bot):
    return ScheduledPublicationWorker(
        store,
        store,
        FakeVerifier(ProductPreview(current_price=100.0, in_stock=True)),
        bot,
        main_channel_id="-100-main",
        admin_chat_id="123-admin",
    )


@pytest.mark.asyncio
async def test_fallo_de_bd_en_la_segunda_no_deshace_ni_reenvia_la_primera():
    first, second = scheduled_deal(), scheduled_deal()
    first.id, second.id = "first", "second"
    store = TransactionalStore([first, second], fail_update_for="second")
    bot = FakeBot()
    worker = _store_worker(store, bot)
    now = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)

    processed = await worker.process_due(now)

    assert processed == 2
    assert store.committed == {
        "first": ScheduledDealStatus.PUBLISHED,
        "second": ScheduledDealStatus.SCHEDULED,
    }
    assert len(bot.posts) == 2

    # Siguiente tick con la BD recuperada: solo se reintenta la segunda.
    store.fail_update_for = None
    assert await worker.process_due(now) == 1
    assert len(bot.posts) == 3
    assert store.committed["second"] == ScheduledDealStatus.PUBLISHED


@pytest.mark.asyncio
async def test_omite_la_programacion_bloqueada_por_otro_proceso():
    first, second = scheduled_deal(), scheduled_deal()
    first.id, second.id = "first", "second"
    store = TransactionalStore([first, second])
    store.locked_elsewhere.add("first")
    bot = FakeBot()

    processed = await _store_worker(store, bot).process_due(datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc))

    assert processed == 1
    assert store.committed == {
        "first": ScheduledDealStatus.SCHEDULED,
        "second": ScheduledDealStatus.PUBLISHED,
    }
    assert len(bot.posts) == 1


# ── Tarjeta de oferta (imagen «Simple claro») ────────────────────────────────

class CardBot(FakeBot):
    """Bot que sabe descargar la foto y enviar imágenes generadas."""

    def __init__(self, card_ok=True):
        super().__init__()
        self.card_ok = card_ok
        self.cards = []

    def download_image(self, url):
        import io

        from PIL import Image

        out = io.BytesIO()
        Image.new("RGB", (300, 300), (200, 30, 30)).save(out, format="PNG")
        return out.getvalue()

    def send_photo_bytes(self, content, chat_id=None, caption="", entities=None):
        self.cards.append({"content": content, "chat_id": chat_id, "caption": caption, "entities": entities})
        return self.card_ok


@pytest.mark.asyncio
async def test_publica_con_la_tarjeta_de_oferta_y_la_copia_de_whatsapp_tambien():
    scheduled = scheduled_deal()
    scheduled.deal.store = SimpleNamespace(name="Amazon")
    bot = CardBot()
    worker, _ = worker_for(scheduled, ProductPreview(current_price=100.0, in_stock=True), bot)

    await worker.process_due(datetime.now(timezone.utc))

    assert scheduled.status == ScheduledDealStatus.PUBLISHED
    assert bot.posts == []  # sin la foto original
    post, whatsapp = bot.cards
    assert post["chat_id"] == "-100-destination" and post["entities"]
    assert post["content"][:2] == b"\xff\xd8"  # JPEG
    assert whatsapp["chat_id"] == "123-admin" and whatsapp["content"] == post["content"]


@pytest.mark.asyncio
async def test_sin_precio_anterior_publica_la_foto_original():
    scheduled = scheduled_deal()
    scheduled.regular_price = None
    bot = CardBot()
    worker, _ = worker_for(scheduled, ProductPreview(current_price=100.0, in_stock=True), bot)

    await worker.process_due(datetime.now(timezone.utc))

    assert scheduled.status == ScheduledDealStatus.PUBLISHED
    assert bot.cards == [] and len(bot.posts) == 1


@pytest.mark.asyncio
async def test_si_telegram_rechaza_la_tarjeta_se_publica_con_la_foto_original():
    scheduled = scheduled_deal()
    bot = CardBot(card_ok=False)
    worker, _ = worker_for(scheduled, ProductPreview(current_price=100.0, in_stock=True), bot)

    await worker.process_due(datetime.now(timezone.utc))

    assert scheduled.status == ScheduledDealStatus.PUBLISHED
    assert len(bot.posts) == 1 and bot.posts[0]["image_url"] == "https://images.test/product.jpg"
