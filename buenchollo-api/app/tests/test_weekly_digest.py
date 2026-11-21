"""«Los chollos de la semana»: texto, versión WhatsApp y envío al canal Admin."""

import io
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from PIL import Image

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
        image_url=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


WINDOW = wd.week_window(NOW)


def test_semana_de_siete_dias_naturales_en_hora_de_madrid():
    assert wd.week_label(WINDOW) == "16–22 de noviembre"
    assert WINDOW.since.isoformat() == "2026-11-16T00:00:00+01:00"
    other = wd.week_window(datetime(2026, 12, 2, 12, tzinfo=timezone.utc))
    assert wd.week_label(other) == "26 de noviembre – 2 de diciembre"


def test_texto_con_cabecera_chollos_numerados_y_enlace_a_la_web():
    text, count = wd.build_weekly_digest(
        [_deal(1), _deal(2, previous_price=None, discount_percentage=None)], WINDOW, "https://bct.test"
    )
    assert count == 2
    assert text.startswith("📅 Los chollos de la semana · 16–22 de noviembre\n\n")
    assert "🍄 1. Producto 1\n💶 99,99 € (antes 149,99 €) | -33 %\n🛒 https://www.amazon.es/dp/B000000001?tag=x\n" in text
    assert "🍄 2. Producto 2\n💶 99,99 €\n" in text
    assert text.rstrip().endswith(f"🔗 {LINK_TEXT}")


def test_sin_enlace_de_afiliado_usa_la_ficha_de_la_web():
    text, _ = wd.build_weekly_digest([_deal(1, affiliate_url=None)], WINDOW, "https://bct.test/")
    assert "🛒 https://bct.test/chollo/producto-1" in text


def test_calcula_el_descuento_si_falta():
    text, _ = wd.build_weekly_digest(
        [_deal(1, discount_percentage=None, current_price=75, previous_price=100)], WINDOW, "x"
    )
    assert "| -25 %" in text


def test_sin_chollos_no_hay_resumen():
    assert wd.build_weekly_digest([], WINDOW, "x") == (None, 0)


def test_corta_la_lista_si_no_cabe_en_un_mensaje():
    deals = [_deal(i, title="Título muy largo " * 20) for i in range(10)]
    text, count = wd.build_weekly_digest(deals, WINDOW, "x")
    assert len(text) <= wd.MAX_TEXT_LENGTH
    assert text.rstrip().endswith(f"🔗 {LINK_TEXT}")
    assert count == text.count("🍄") < 10


def test_version_whatsapp_con_cabecera_en_negrita():
    text, _ = wd.build_weekly_digest([_deal(1)], WINDOW, "x")
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


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), (200, 30, 30)).save(buf, format="PNG")
    return buf.getvalue()


class FakeBot:
    def __init__(self, ok=True, photo_ok=True):
        self.ok = ok
        self.photo_ok = photo_ok
        self.sent: list[dict] = []
        self.photos: list[bytes] = []
        self.last_error = None

    def download_image(self, url):
        return _png() if url else None

    def send_photo_bytes(self, content, chat_id=None, caption=""):
        self.photos.append(content)
        self.sent.append({"photo": True, "chat_id": chat_id})
        return self.photo_ok

    def send_preformatted(self, *, text, entities, image_url=None, chat_id=None):
        self.sent.append({"text": text, "entities": entities, "chat_id": chat_id})
        return self.ok


class FakeGuard:
    """Bloquea los chollos cuyo enlace de afiliado esté en `blocked`."""

    def __init__(self, blocked=()):
        self.blocked = set(blocked)

    async def blockers_for(self, data):
        return ["affiliate_program"] if data["affiliate_url"] in self.blocked else []


def _service(deals, bot, chat="-100admin", guard=None):
    return wd.WeeklyDigestService(
        FakeRepo(deals), bot, lambda t: [{"type": "bold"}], chat, "https://bct.test", guard=guard
    )


@pytest.mark.asyncio
async def test_preview_pide_la_semana_y_publica_10_como_mucho():
    service = _service([_deal(i) for i in range(1, 15)], FakeBot())
    digest = await service.preview(NOW)
    assert service.deal_repo.args == (WINDOW.since, 25)
    assert digest.count == 10 and digest.telegram_text and digest.whatsapp_text


@pytest.mark.asyncio
async def test_omite_los_chollos_de_redes_que_ya_no_cumplen_las_reglas():
    awin_url = "https://www.awin1.com/cread.php?awinmid=1"
    awin = _deal(1, affiliate_url=awin_url, data_source="awin")
    service = _service([awin, _deal(2)], FakeBot(), guard=FakeGuard(blocked={awin_url}))
    digest = await service.preview(NOW)
    assert digest.count == 1
    assert "Producto 1" not in digest.telegram_text and "1. Producto 2" in digest.telegram_text


@pytest.mark.asyncio
async def test_envia_collage_y_las_dos_versiones_al_canal_admin():
    bot = FakeBot()
    service = _service([_deal(1, image_url="https://img/1.jpg"), _deal(2, image_url=None)], bot)
    assert service.send(await service.preview(NOW)) is True
    assert [m["chat_id"] for m in bot.sent] == ["-100admin"] * 3
    assert bot.sent[0] == {"photo": True, "chat_id": "-100admin"}
    assert bot.sent[1]["entities"] == [{"type": "bold"}]
    assert bot.sent[2]["entities"] == [] and bot.sent[2]["text"].startswith("*📅")
    with Image.open(io.BytesIO(bot.photos[0])) as collage:
        assert (collage.format, collage.size) == ("JPEG", (1600, 900))


@pytest.mark.asyncio
async def test_si_falla_el_collage_el_texto_sale_igual():
    bot = FakeBot(photo_ok=False)
    service = _service([_deal(1, image_url="https://img/1.jpg")], bot)
    assert service.send(await service.preview(NOW)) is True
    assert len([m for m in bot.sent if "text" in m]) == 2


@pytest.mark.asyncio
async def test_si_no_se_puede_generar_el_collage_el_texto_sale_igual(monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("Pillow roto")

    monkeypatch.setattr(wd, "build_collage", boom)
    bot = FakeBot()
    service = _service([_deal(1, image_url="https://img/1.jpg")], bot)
    assert service.send(await service.preview(NOW)) is True
    assert bot.photos == [] and len(bot.sent) == 2


def test_collage_con_fuente_de_la_web_y_huecos_sin_imagen():
    from app.modules.telegram.application.weekly_collage import CollageItem, _font, build_collage

    assert "Space Grotesk" in " ".join(_font(30).getname())
    items = [CollageItem(i, _png() if i % 2 else None, "1.299,00 €", 42 if i % 3 else None) for i in range(1, 8)]
    with Image.open(io.BytesIO(build_collage(items, "LOS CHOLLOS DE LA SEMANA", "16–22 de noviembre"))) as img:
        assert img.size == (1600, 900)


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
    assert len([m for m in bot.sent if "text" in m]) == 1


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
