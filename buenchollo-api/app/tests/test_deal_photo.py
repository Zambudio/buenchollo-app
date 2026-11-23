"""Foto de cada publicación de chollo: tarjeta de oferta o foto original."""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.config import get_settings
from app.modules.telegram.application import deal_photo
from app.modules.telegram.application.deal_card import DealCardData
from app.modules.telegram.application.deal_photo import (
    card_data,
    deal_card_data,
    render_card,
    send_deal_post,
    store_name_of,
)
from app.modules.telegram.application.whatsapp_copy import send_whatsapp_copy


class FakeBot:
    def __init__(self, *, image=b"foto", photo_ok=True, unknown=False):
        self.image = image
        self.photo_ok = photo_ok
        self.unknown = unknown
        self.calls = []
        self.last_delivery_unknown = False
        self.last_error = None

    def download_image(self, url):
        self.calls.append(("download", url))
        return self.image

    def send_photo_bytes(self, content, chat_id=None, caption="", entities=None):
        self.calls.append(("bytes", content, caption))
        self.last_delivery_unknown = self.unknown
        return self.photo_ok

    def send_preformatted(self, text, entities, image_url=None, chat_id=None):
        self.calls.append(("url", image_url, text))
        return True


@pytest.fixture(autouse=True)
def _card_on(monkeypatch):
    monkeypatch.setattr(deal_photo, "build_deal_card", lambda data, image: b"TARJETA")
    yield


def _data():
    return DealCardData(99, 159, "Amazon")


# ── Datos ────────────────────────────────────────────────────────────────────

def test_card_data_converts_decimals_and_strips_store():
    assert card_data(Decimal("99.90"), Decimal("159"), " Coolmod ") == DealCardData(99.9, 159.0, "Coolmod")
    assert card_data(None, 159, "Amazon") is None
    assert card_data("no es un número", 159, "Amazon") is None
    assert card_data(99, None, None) == DealCardData(99.0, None, "")


def test_deal_card_data_and_store_name():
    deal = SimpleNamespace(current_price=Decimal("18.51"), previous_price=Decimal("29.99"),
                           store=SimpleNamespace(name="Amazon"))
    assert deal_card_data(deal) == DealCardData(18.51, 29.99, "Amazon")
    assert store_name_of(SimpleNamespace(store=None)) is None
    assert store_name_of(SimpleNamespace(store=SimpleNamespace(name=object()))) is None
    assert store_name_of(None) is None


# ── Render ───────────────────────────────────────────────────────────────────

def test_render_card_downloads_and_builds():
    bot = FakeBot()
    assert render_card(bot, "https://img/x.jpg", _data()) == b"TARJETA"
    assert bot.calls == [("download", "https://img/x.jpg")]


@pytest.mark.parametrize("image_url, data", [(None, _data()), ("https://img/x.jpg", None)])
def test_render_card_without_url_or_data(image_url, data):
    bot = FakeBot()
    assert render_card(bot, image_url, data) is None
    assert bot.calls == []


def test_render_card_when_the_photo_does_not_download():
    assert render_card(FakeBot(image=None), "https://img/x.jpg", _data()) is None


def test_render_card_never_raises():
    class Broken(FakeBot):
        def download_image(self, url):
            raise RuntimeError("red caída")

    assert render_card(Broken(), "https://img/x.jpg", _data()) is None


def test_render_card_disabled_by_setting(monkeypatch):
    monkeypatch.setenv("DEAL_CARD_ENABLED", "false")
    get_settings.cache_clear()
    try:
        bot = FakeBot()
        assert render_card(bot, "https://img/x.jpg", _data()) is None
        assert bot.calls == []
    finally:
        get_settings.cache_clear()


# ── Envío ────────────────────────────────────────────────────────────────────

def test_send_with_card():
    bot = FakeBot()
    assert send_deal_post(bot, text="post", entities=[], image_url="u", chat_id="c", card=b"T")
    assert bot.calls == [("bytes", b"T", "post")]


def test_send_without_card_uses_the_original_photo():
    bot = FakeBot()
    assert send_deal_post(bot, text="post", entities=[], image_url="u", chat_id="c", card=None)
    assert bot.calls == [("url", "u", "post")]


def test_rejected_card_falls_back_to_the_original_photo():
    bot = FakeBot(photo_ok=False)
    assert send_deal_post(bot, text="post", entities=[], image_url="u", chat_id="c", card=b"T")
    assert [c[0] for c in bot.calls] == ["bytes", "url"]


def test_unknown_delivery_is_not_resent():
    # Sin respuesta de Telegram la foto pudo llegar: no se duplica el post.
    bot = FakeBot(photo_ok=False, unknown=True)
    assert send_deal_post(bot, text="post", entities=[], image_url="u", chat_id="c", card=b"T")
    assert [c[0] for c in bot.calls] == ["bytes"]


# ── Copia de WhatsApp ────────────────────────────────────────────────────────

def test_whatsapp_copy_uses_the_card():
    bot = FakeBot()
    assert send_whatsapp_copy(bot, chat_id="admin", telegram_text="🍄 Chollo", image_url="u", image_bytes=b"T")
    assert bot.calls[0][0] == "bytes"


def test_whatsapp_copy_falls_back_to_the_original_photo():
    bot = FakeBot(photo_ok=False)
    assert send_whatsapp_copy(bot, chat_id="admin", telegram_text="🍄 Chollo", image_url="u", image_bytes=b"T")
    assert [c[0] for c in bot.calls] == ["bytes", "url"]


# ── /telegram/notify (panel) ─────────────────────────────────────────────────

def test_notify_publica_con_la_tarjeta_usando_precio_y_tienda_del_panel(monkeypatch):
    import io
    from unittest.mock import AsyncMock, MagicMock

    from fastapi.testclient import TestClient
    from PIL import Image

    from app.core.config import Settings, get_settings
    from app.core.database import get_db
    from app.core.security import require_admin
    from app.main import app

    monkeypatch.undo()  # tarjeta real, no la simulada del fixture

    class User:
        id = "admin-1"

    async def _admin():
        return User()

    async def _db():
        session = MagicMock()
        session.execute = AsyncMock(side_effect=RuntimeError("sin BD"))
        session.rollback = AsyncMock()
        yield session

    photo = io.BytesIO()
    Image.new("RGB", (300, 300), (10, 120, 200)).save(photo, format="PNG")
    bot = MagicMock()
    bot.download_image.return_value = photo.getvalue()
    bot.send_photo_bytes.return_value = True
    bot.last_message_id = 7

    async def _record(*_a, **_k):
        return True

    monkeypatch.setattr("app.modules.telegram.api.router.TelegramBot", lambda token: bot)
    monkeypatch.setattr("app.modules.telegram.api.router.record_safely", _record)
    app.dependency_overrides[require_admin] = _admin
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_settings] = lambda: Settings(
        telegram_enabled=True, telegram_bot_token="tok", telegram_main_channel_id="-100main",
        telegram_admin_channel_id="-100admin",
    )
    try:
        resp = TestClient(app).post(
            "/v1/telegram/notify",
            json={"text": "🍄 Webcam\n\n🛒 https://amzn.to/x", "channel_id": "-100main",
                  "image_url": "https://img/x.jpg", "current_price": 18.51, "previous_price": 29.99,
                  "store_name": "Amazon"},
        )
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 200, resp.text
    assert not bot.send_preformatted.called  # ni foto original ni texto suelto
    post, whatsapp = bot.send_photo_bytes.call_args_list
    assert post.kwargs["chat_id"] == "-100main"
    assert post.args[0][:2] == b"\xff\xd8"
    assert whatsapp.kwargs["chat_id"] == "-100admin" and whatsapp.args[0] == post.args[0]


def test_card_data_takes_the_post_discount():
    assert card_data(80, 100, "Amazon", 12).discount == 12
    assert card_data(80, 100, "Amazon", 0).discount is None  # se calcula
    assert card_data(80, 100, "Amazon", None).discount is None


def test_whatsapp_copy_does_not_resend_after_an_unknown_delivery():
    bot = FakeBot(photo_ok=False, unknown=True)
    assert send_whatsapp_copy(bot, chat_id="admin", telegram_text="🍄 Chollo", image_url="u", image_bytes=b"T")
    assert [c[0] for c in bot.calls] == ["bytes"]


def test_notify_card_uses_only_the_panel_prices():
    # Antes vacío en el panel: no se completa con el del chollo guardado.
    from app.modules.telegram.api.router import _notify_card_data
    from app.modules.telegram.api.schemas import TelegramNotifyRequest

    deal = SimpleNamespace(current_price=Decimal("80"), previous_price=Decimal("100"),
                           discount_percentage=20, store=SimpleNamespace(name="Amazon"))
    payload = TelegramNotifyRequest(text="x", current_price=80, previous_price=None)
    assert _notify_card_data(payload, deal) == DealCardData(80.0, None, "Amazon")
    payload = TelegramNotifyRequest(text="x", current_price=80, previous_price=100, discount_percentage=19)
    assert _notify_card_data(payload, deal).discount == 19
    # Panel antiguo sin precios: los del chollo, con su descuento.
    assert _notify_card_data(TelegramNotifyRequest(text="x"), deal) == DealCardData(80.0, 100.0, "Amazon", 20)
