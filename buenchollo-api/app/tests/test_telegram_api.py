"""Tests de POST /telegram/notify.

Cubre TD-06: los errores de negocio del módulo ya no lanzan `HTTPException`
directa, sino excepciones de dominio (`app/modules/telegram/domain/exceptions.py`)
traducidas por el handler global. Verifica que los status codes se preservan
tal cual estaban antes del refactor (503/503/422/503).
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.rate_limit import limiter
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
    settings = Settings(**{"telegram_enabled": True, **overrides})
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


def test_notify_envia_a_telegram_fuera_del_event_loop(client, monkeypatch):
    limiter.reset()  # /notify limita a 5/min por IP en todo el proceso de tests
    _override_settings(telegram_bot_token="tok", telegram_main_channel_id="chan")

    def _send_deal(**kwargs):
        # En el hilo del event loop habría un loop en marcha: el envío
        # (requests, bloqueante) debe ejecutarse en el threadpool.
        with pytest.raises(RuntimeError):
            asyncio.get_running_loop()
        return False

    fake_bot = MagicMock()
    fake_bot.send_deal.side_effect = _send_deal
    monkeypatch.setattr(
        "app.modules.telegram.api.router.TelegramBot", lambda token: fake_bot
    )

    r = client.post(
        "/v1/telegram/notify", json={"title": "Deal", "current_price": 9.99}
    )

    fake_bot.send_deal.assert_called_once()
    assert r.status_code == 503


# ── POST /telegram/generate con copy de IA (chollo ya guardado) ──────────────

_GENERATE_BASE = {
    "title": "DJI Osmo Pocket 3",
    "current_price": 269.0,
    "previous_price": 429.0,
    "discount_percentage": 37,
    "description": "Captura cada momento",
    "affiliate_url": "https://amzn.to/x",
}


def _patch_generator(monkeypatch, copy):
    calls = {}

    async def fake_copy(self, title, details, provider=None):
        calls.update(title=title, details=details, provider=provider)
        return copy

    async def fake_suggest(self, title, description, available):
        return []

    gen = "app.modules.telegram.application.post_generator.TelegramPostGenerator"
    monkeypatch.setattr(f"{gen}.generate_copy", fake_copy)
    monkeypatch.setattr(f"{gen}.suggest_categories", fake_suggest)
    return calls


def test_generate_con_ai_copy_usa_el_texto_de_la_ia(client, monkeypatch):
    _override_settings()
    calls = _patch_generator(monkeypatch, "Gimbal de bolsillo con sensor de 1 pulgada.")

    r = client.post(
        "/v1/telegram/generate",
        json={**_GENERATE_BASE, "ai_copy": True, "provider": "openai", "copy_context": "Sensor 1''"},
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ai_copy"] == "Gimbal de bolsillo con sensor de 1 pulgada."
    assert "✏️Gimbal de bolsillo con sensor de 1 pulgada." in body["text"]
    assert "Captura cada momento" not in body["text"]
    # Hay rebaja: el precio va en la tarjeta de oferta, no en el texto.
    assert "💶" not in body["text"]
    assert calls == {"title": "DJI Osmo Pocket 3", "details": "Sensor 1''", "provider": "openai"}


def test_generate_si_la_ia_falla_usa_la_descripcion(client, monkeypatch):
    _override_settings()
    _patch_generator(monkeypatch, None)

    r = client.post("/v1/telegram/generate", json={**_GENERATE_BASE, "ai_copy": True})

    assert r.status_code == 200, r.text
    assert r.json()["ai_copy"] is None
    assert "✏️Captura cada momento" in r.json()["text"]


def test_generate_sin_ai_copy_no_llama_a_la_ia(client, monkeypatch):
    _override_settings()
    calls = _patch_generator(monkeypatch, "no debería usarse")

    r = client.post("/v1/telegram/generate", json=_GENERATE_BASE)

    assert r.status_code == 200, r.text
    assert calls == {}
    assert r.json()["ai_copy"] is None


def test_generate_rechaza_proveedor_desconocido(client):
    _override_settings()

    r = client.post(
        "/v1/telegram/generate", json={**_GENERATE_BASE, "ai_copy": True, "provider": "otro"}
    )

    assert r.status_code == 422


# ── Versión WhatsApp del post ────────────────────────────────────────────────

def test_generate_devuelve_tambien_la_version_whatsapp(client, monkeypatch):
    _override_settings()
    _patch_generator(monkeypatch, None)

    r = client.post("/v1/telegram/generate", json=_GENERATE_BASE)

    assert r.status_code == 200, r.text
    whatsapp = r.json()["whatsapp_text"]
    assert whatsapp.startswith("🔥 *DJI Osmo Pocket 3*")
    assert "🍄" not in whatsapp


def test_whatsapp_text_convierte_el_texto_editado(client):
    _override_settings()

    r = client.post("/v1/telegram/whatsapp-text", json={"text": "🍄 Editado\n\n🛒 https://amzn.to/y"})

    assert r.status_code == 200, r.text
    assert r.json() == {"text": "🔥 *Editado*\n\n👉 https://amzn.to/y"}


def test_whatsapp_text_requiere_admin():
    app.dependency_overrides.clear()

    r = TestClient(app).post("/v1/telegram/whatsapp-text", json={"text": "x"})

    assert r.status_code in (401, 403)


def test_notify_del_panel_envia_tambien_la_version_whatsapp_al_canal_admin(client, monkeypatch):
    limiter.reset()
    _override_settings(
        telegram_bot_token="tok", telegram_main_channel_id="-100main", telegram_admin_channel_id="-100admin",
        whatsapp_enabled=False,
    )
    fake_bot = MagicMock()
    fake_bot.send_preformatted.return_value = True
    fake_bot.last_message_id = 7
    router = "app.modules.telegram.api.router"
    monkeypatch.setattr(f"{router}.TelegramBot", lambda token: fake_bot)
    monkeypatch.setattr(f"{router}.record_safely", AsyncMock(return_value=True))
    monkeypatch.setattr(f"{router}.audit_log", AsyncMock())

    r = client.post(
        "/v1/telegram/notify",
        json={
            "text": "🍄 Monitor\n\n🛒 https://amzn.to/x",
            "image_url": "https://img/x.jpg",
            "channel_id": "-100main",
            "whatsapp_text": "🔥 *Monitor editado*",
        },
    )

    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True, "whatsapp_sent": True}
    telegram, whatsapp = (call.kwargs for call in fake_bot.send_preformatted.call_args_list)
    assert telegram["chat_id"] == "-100main" and telegram["entities"]
    assert whatsapp == {
        "text": "🔥 *Monitor editado*", "entities": [], "image_url": "https://img/x.jpg", "chat_id": "-100admin",
    }


def test_con_whatsapp_automatico_no_manda_la_copia_al_admin(client, monkeypatch):
    limiter.reset()
    _override_settings(
        telegram_bot_token="tok", telegram_main_channel_id="-100main", telegram_admin_channel_id="-100admin",
        whatsapp_enabled=True,
    )
    fake_bot = MagicMock()
    fake_bot.send_preformatted.return_value = True
    fake_bot.last_message_id = 7
    router = "app.modules.telegram.api.router"
    published = []

    async def fake_publish(event):
        published.append(event)

    monkeypatch.setattr(f"{router}.TelegramBot", lambda token: fake_bot)
    monkeypatch.setattr(f"{router}.record_safely", AsyncMock(return_value=True))
    monkeypatch.setattr(f"{router}.audit_log", AsyncMock())
    monkeypatch.setattr(f"{router}.events.publish", fake_publish)

    r = client.post(
        "/v1/telegram/notify",
        json={"text": "🍄 Monitor\n\n🛒 https://amzn.to/x", "channel_id": "-100main", "whatsapp_text": "🔥 *Editado*"},
    )

    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True, "whatsapp_sent": False}
    assert [c.kwargs["chat_id"] for c in fake_bot.send_preformatted.call_args_list] == ["-100main"]
    assert published[0].whatsapp_text == "🔥 *Editado*"  # la versión editada llega a la cola de WhatsApp


# ── Aviso del programa: lo decide el servidor, no el navegador ───────────────

class _FakeProgram:
    def __init__(self, disclosure_text):
        self.disclosure_text = disclosure_text


def _patch_program(monkeypatch, program):
    async def fake_get_program(self, program_id):
        return program

    monkeypatch.setattr(
        "app.modules.affiliates.infrastructure.repository.AffiliateRepository.get_program", fake_get_program
    )


_PROGRAM_ID = "7c6a3048-c2d4-434e-833e-b9e97ba2b54d"


def test_generate_ignora_el_aviso_que_manda_el_navegador(client, monkeypatch):
    # Una pestaña abierta desde antes de vaciar el aviso lo seguía enviando.
    _override_settings()
    _patch_generator(monkeypatch, None)
    _patch_program(monkeypatch, _FakeProgram(None))

    r = client.post(
        "/v1/telegram/generate",
        json={**_GENERATE_BASE, "affiliate_program_id": _PROGRAM_ID, "notice": "Enlace de afiliado: podemos recibir…"},
    )

    assert r.status_code == 200, r.text
    assert "podemos recibir" not in r.json()["text"]


def test_generate_usa_el_aviso_guardado_del_programa(client, monkeypatch):
    _override_settings()
    _patch_generator(monkeypatch, None)
    _patch_program(monkeypatch, _FakeProgram("Aviso exigido por la tienda"))

    r = client.post("/v1/telegram/generate", json={**_GENERATE_BASE, "affiliate_program_id": _PROGRAM_ID})

    assert r.status_code == 200, r.text
    assert "ℹ️ Aviso exigido por la tienda" in r.json()["text"]


def test_generate_sin_programa_no_lleva_aviso(client, monkeypatch):
    _override_settings()
    _patch_generator(monkeypatch, None)

    r = client.post("/v1/telegram/generate", json={**_GENERATE_BASE, "notice": "Texto viejo"})

    assert r.status_code == 200, r.text
    assert "Texto viejo" not in r.json()["text"]
    assert "ℹ️" not in r.json()["text"]



def test_generate_sin_rebaja_mantiene_el_precio_en_el_texto(client, monkeypatch):
    # Sin precio anterior no hay tarjeta: el precio sigue en el texto.
    _override_settings()
    _patch_generator(monkeypatch, None)

    r = client.post("/v1/telegram/generate", json={**_GENERATE_BASE, "previous_price": None})

    assert r.status_code == 200, r.text
    assert "💶 Precio: 269,00 €" in r.json()["text"]


# ── Otras redes: /notify anuncia el chollo publicado por el bus de eventos ───

def test_notify_anuncia_el_chollo_publicado_sin_conocer_a_los_suscriptores(client, monkeypatch):
    from app.core import events

    limiter.reset()
    _override_settings(telegram_bot_token="tok", telegram_main_channel_id="-100main")
    fake_bot = MagicMock()
    fake_bot.send_preformatted.return_value = True
    fake_bot.download_image.return_value = None
    router = "app.modules.telegram.api.router"
    monkeypatch.setattr(f"{router}.TelegramBot", lambda token: fake_bot)
    monkeypatch.setattr(f"{router}.record_safely", AsyncMock(return_value=True))
    monkeypatch.setattr(f"{router}.audit_log", AsyncMock())
    published = []

    async def fake_publish(event):
        published.append(event)

    monkeypatch.setattr(events, "publish", fake_publish)
    text = "🍄 Monitor\n\n🛒 https://amzn.to/x"

    r = client.post(
        "/v1/telegram/notify", json={"text": text, "image_url": "https://img/x.jpg", "channel_id": "-100main"}
    )

    assert r.status_code == 200, r.text
    (event,) = [e for e in published if isinstance(e, events.DealPostPublished)]
    assert (event.channel_id, event.text, event.image_url, event.card) == ("-100main", text, "https://img/x.jpg", None)
    assert event.download == fake_bot.download_image
