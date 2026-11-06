"""Registro de lo que se publica en Telegram (petición de Pedro, 2026-11-06).

Hasta ahora el panel generaba y enviaba la publicación sin guardarla. Ahora
queda registrada con su texto, imagen, canal y precios del chollo, para poder
reenviarla corregida cuando el chollo vuelve a estar en oferta.
"""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import Settings
from app.modules.telegram.application.publications import channel_kind, record_publication
from app.modules.telegram.infrastructure.telegram_bot import TelegramBot

SETTINGS = Settings(telegram_enabled=True, telegram_main_channel_id="-100main", telegram_admin_channel_id="-100admin")


def _deal(**overrides):
    base = dict(id="deal-1", current_price=Decimal("59.90"), previous_price=Decimal("99.99"), discount_percentage=40)
    base.update(overrides)
    return SimpleNamespace(**base)


class FakeRepo:
    def __init__(self):
        self.saved = []

    async def add(self, publication):
        self.saved.append(publication)
        return publication


def _deal_repo(by_id=None, by_asin=None):
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=by_id)
    repo.find_by_external_id = AsyncMock(return_value=by_asin)
    return repo


def test_channel_kind():
    assert channel_kind("-100main", SETTINGS) == "main"
    assert channel_kind("-100admin", SETTINGS) == "admin"
    assert channel_kind("-100otro", SETTINGS) == "other"


@pytest.mark.asyncio
async def test_registra_con_deal_id_y_guarda_los_precios_del_momento():
    repo = FakeRepo()
    pub = await record_publication(
        repo, _deal_repo(by_id=_deal()), text="🍄 Monitor", channel_id="-100main", kind="main",
        source="panel", image_url="https://img/x.jpg", deal_id="deal-1", message_id=77, sent_by="admin-1",
    )
    assert repo.saved == [pub]
    assert (pub.deal_id, pub.channel_kind, pub.source, pub.telegram_message_id) == ("deal-1", "main", "panel", 77)
    assert (pub.price, pub.previous_price, pub.discount_percentage) == (Decimal("59.90"), Decimal("99.99"), 40)
    assert pub.text == "🍄 Monitor" and pub.image_url == "https://img/x.jpg" and pub.sent_by == "admin-1"


@pytest.mark.asyncio
async def test_sin_deal_id_lo_busca_por_el_asin_del_enlace():
    deal_repo = _deal_repo(by_asin=_deal(id="deal-asin"))
    pub = await record_publication(
        FakeRepo(), deal_repo, text="t", channel_id="-100main", kind="main", source="panel",
        affiliate_url="https://www.amazon.es/dp/b0d9wh9wld?tag=bct-21",
    )
    deal_repo.find_by_external_id.assert_awaited_once_with("B0D9WH9WLD", exclude_id=None)
    assert pub.deal_id == "deal-asin"


@pytest.mark.asyncio
async def test_sin_chollo_conocido_se_registra_igual():
    pub = await record_publication(
        FakeRepo(), _deal_repo(), text="t", channel_id="-100main", kind="main", source="panel",
        affiliate_url="https://www.pccomponentes.com/x",
    )
    assert pub.deal_id is None and pub.price is None


def test_el_bot_guarda_el_message_id_de_telegram(monkeypatch):
    class Resp:
        ok = True

        def json(self):
            return {"ok": True, "result": {"message_id": 4242}}

    monkeypatch.setattr("app.modules.telegram.infrastructure.telegram_bot.requests.post", lambda *a, **k: Resp())
    bot = TelegramBot("tok")
    assert bot.send_preformatted(text="hola", entities=[], chat_id="-100main") is True
    assert bot.last_message_id == 4242


def test_notify_del_panel_registra_la_publicacion(monkeypatch):
    from fastapi.testclient import TestClient

    from app.core.config import get_settings
    from app.core.database import get_db
    from app.core.security import require_admin
    from app.main import app

    class User:
        id = "admin-1"

    async def _admin():
        return User()

    async def _db():
        session = MagicMock()
        session.execute = AsyncMock(return_value=MagicMock())
        session.add = MagicMock()
        session.flush = AsyncMock()
        yield session

    fake_bot = MagicMock()
    fake_bot.send_preformatted.return_value = True
    fake_bot.last_message_id = 9
    recorded = {}

    async def _record(repo, deal_repo, **kwargs):
        recorded.update(kwargs)

    monkeypatch.setattr("app.modules.telegram.api.router.TelegramBot", lambda token: fake_bot)
    monkeypatch.setattr("app.modules.telegram.api.router.record_publication", _record)
    app.dependency_overrides[require_admin] = _admin
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_settings] = lambda: Settings(
        telegram_enabled=True, telegram_bot_token="tok", telegram_main_channel_id="-100main"
    )
    try:
        resp = TestClient(app).post(
            "/v1/telegram/notify",
            json={"text": "🍄 Monitor", "channel_id": "-100main", "image_url": "https://img/x.jpg",
                  "deal_id": "deal-1", "affiliate_url": "https://www.amazon.es/dp/B0D9WH9WLD"},
        )
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 200, resp.text
    assert recorded["deal_id"] == "deal-1" and recorded["text"] == "🍄 Monitor"
    assert recorded["kind"] == "main" and recorded["source"] == "panel" and recorded["message_id"] == 9
