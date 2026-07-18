"""Tests de POST /telegram/notify.

Cubre TD-06: los errores de negocio del módulo ya no lanzan `HTTPException`
directa, sino excepciones de dominio (`app/modules/telegram/domain/exceptions.py`)
traducidas por el handler global. Verifica que los status codes se preservan
tal cual estaban antes del refactor (503/503/422/503).
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import require_admin
from app.main import app


class MockUser:
    id = "dbe6e006-4f3e-4be8-8351-7e264ed3acb6"


async def mock_require_admin():
    return MockUser()


async def _fake_db():
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock())
    yield session


@pytest.fixture
def client():
    app.dependency_overrides[require_admin] = mock_require_admin
    app.dependency_overrides[get_db] = _fake_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _override_settings(**overrides):
    settings = Settings(**overrides)
    app.dependency_overrides[get_settings] = lambda: settings
    return settings


def test_notify_sin_bot_token_devuelve_503(client):
    _override_settings(telegram_bot_token="")

    r = client.post("/v1/telegram/notify", json={"title": "Deal", "current_price": 9.99})

    assert r.status_code == 503
    assert "TELEGRAM_BOT_TOKEN" in r.json()["detail"]


def test_notify_sin_canal_devuelve_503(client):
    _override_settings(telegram_bot_token="tok", telegram_main_channel_id="")

    r = client.post("/v1/telegram/notify", json={"title": "Deal", "current_price": 9.99})

    assert r.status_code == 503
    assert "TELEGRAM_MAIN_CHANNEL_ID" in r.json()["detail"]


def test_notify_payload_incompleto_devuelve_422(client):
    _override_settings(telegram_bot_token="tok", telegram_main_channel_id="chan")

    r = client.post("/v1/telegram/notify", json={})

    assert r.status_code == 422
    assert "text" in r.json()["detail"]


def test_notify_fallo_envio_devuelve_503(client, monkeypatch):
    _override_settings(telegram_bot_token="tok", telegram_main_channel_id="chan")

    fake_bot = MagicMock()
    fake_bot.send_deal.return_value = False
    monkeypatch.setattr(
        "app.modules.telegram.api.router.TelegramBot", lambda token: fake_bot
    )

    r = client.post(
        "/v1/telegram/notify", json={"title": "Deal", "current_price": 9.99}
    )

    assert r.status_code == 503
    assert "Error al enviar a Telegram" in r.json()["detail"]
