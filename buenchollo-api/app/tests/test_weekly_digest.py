"""«Los chollos de la semana»: texto, versión WhatsApp y envío al canal Admin."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.modules.telegram.application import weekly_digest as wd
from app.modules.telegram.application.post_generator import LINK_TEXT

# Domingo 22 de noviembre de 2026, 22:30 en Madrid.
NOW = datetime(2026, 11, 22, 21, 30, tzinfo=timezone.utc)


def _deal(i: int, **overrides):
    base = dict(
        title=f"Producto {i}",
        slug=f"producto-{i}",
        current_price=Decimal("99.99"),
        previous_price=Decimal("149.99"),
        discount_percentage=33,
        affiliate_url=f"https://www.amazon.es/dp/B00000000{i}?tag=x",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_week_label():
    assert wd.week_label(NOW) == "16–22 de noviembre"
    assert wd.week_label(datetime(2026, 12, 2, 12, tzinfo=timezone.utc)) == "26 de noviembre – 2 de diciembre"


def test_texto_con_cabecera_chollos_numerados_y_enlace_a_la_web():
    text = wd.build_weekly_digest([_deal(1), _deal(2, previous_price=None, discount_percentage=None)], NOW, "https://bct.test")
    assert text.startswith("📅 Los chollos de la semana · 16–22 de noviembre\n\n")
    assert "🍄 1. Producto 1\n💶 99,99 € (antes 149,99 €) | -33 %\n🛒 https://www.amazon.es/dp/B000000001?tag=x\n" in text
    assert "🍄 2. Producto 2\n💶 99,99 €\n" in text
    assert text.rstrip().endswith(f"🔗 {LINK_TEXT}")


def test_sin_enlace_de_afiliado_usa_la_ficha_de_la_web():
    text = wd.build_weekly_digest([_deal(1, affiliate_url=None)], NOW, "https://bct.test/")
    assert "🛒 https://bct.test/chollo/producto-1" in text


def test_calcula_el_descuento_si_falta():
    text = wd.build_weekly_digest([_deal(1, discount_percentage=None, current_price=75, previous_price=100)], NOW, "x")
    assert "| -25 %" in text


def test_sin_chollos_no_hay_resumen():
    assert wd.build_weekly_digest([], NOW, "x") is None


def test_corta_la_lista_si_no_cabe_en_un_mensaje():
    deals = [_deal(i, title="Título muy largo " * 20) for i in range(10)]
    text = wd.build_weekly_digest(deals, NOW, "x")
    assert len(text) <= wd.MAX_TEXT_LENGTH
    assert text.rstrip().endswith(f"🔗 {LINK_TEXT}")
    assert text.count("🍄") < 10


def test_version_whatsapp_con_cabecera_en_negrita():
    text = wd.build_weekly_digest([_deal(1)], NOW, "x")
    wa = wd.whatsapp_version(text)
    assert wa.startswith("*📅 Los chollos de la semana · 16–22 de noviembre*\n")
    assert "🔥 *1. Producto 1*" in wa
    assert "👉 https://www.amazon.es/dp/B000000001?tag=x" in wa
    assert "🌐 Todos los chollos en nuestra web: https://buenchollotech.com/whatsapp" in wa


class FakeRepo:
    def __init__(self, deals):
        self.deals = deals
        self.args = None

    async def get_top_discount_active_since(self, since, limit):
        self.args = (since, limit)
        return self.deals


class FakeBot:
    def __init__(self, ok=True):
        self.ok = ok
        self.sent: list[dict] = []
        self.last_error = None

    def send_preformatted(self, *, text, entities, image_url=None, chat_id=None):
        self.sent.append({"text": text, "entities": entities, "chat_id": chat_id})
        return self.ok


def _service(deals, bot, chat="-100admin"):
    return wd.WeeklyDigestService(FakeRepo(deals), bot, lambda t: [{"type": "bold"}], chat, "https://bct.test")


@pytest.mark.asyncio
async def test_preview_pide_la_ultima_semana_y_top_10():
    service = _service([_deal(1)], FakeBot())
    digest = await service.preview(NOW)
    assert service.deal_repo.args == (NOW - timedelta(days=7), 10)
    assert digest.count == 1 and digest.telegram_text and digest.whatsapp_text


@pytest.mark.asyncio
async def test_envia_las_dos_versiones_al_canal_admin():
    bot = FakeBot()
    service = _service([_deal(1)], bot)
    assert service.send(await service.preview(NOW)) is True
    assert [m["chat_id"] for m in bot.sent] == ["-100admin", "-100admin"]
    assert bot.sent[0]["entities"] == [{"type": "bold"}]
    assert bot.sent[1]["entities"] == [] and bot.sent[1]["text"].startswith("*📅")


@pytest.mark.asyncio
async def test_sin_chollos_o_sin_canal_no_envia():
    bot = FakeBot()
    assert _service([], bot).send(await _service([], bot).preview(NOW)) is False
    service = _service([_deal(1)], bot, chat="")
    assert service.send(await service.preview(NOW)) is False
    assert bot.sent == []


@pytest.mark.asyncio
async def test_si_telegram_rechaza_no_envia_la_version_whatsapp():
    bot = FakeBot(ok=False)
    service = _service([_deal(1)], bot)
    assert service.send(await service.preview(NOW)) is False
    assert len(bot.sent) == 1


@pytest.mark.asyncio
async def test_job_desactivado_no_hace_nada():
    assert await wd._run(Settings(weekly_digest_enabled=False)) is False


@pytest.mark.asyncio
async def test_job_sin_canal_admin_no_hace_nada():
    assert await wd._run(Settings(telegram_enabled=False)) is False


def test_job_programado_los_domingos_a_las_22_30():
    from app.modules.deals.application.scheduler import build_deals_scheduler

    scheduler, _ = build_deals_scheduler(Settings())
    job = scheduler.get_job("weekly_deals_digest")
    fields = {f.name: str(f) for f in job.trigger.fields}
    assert (fields["day_of_week"], fields["hour"], fields["minute"]) == ("sun", "22", "30")
    assert str(job.trigger.timezone) == "Europe/Madrid"
