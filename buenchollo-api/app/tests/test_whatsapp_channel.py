"""Publicación automática en el Canal de WhatsApp (módulo `whatsapp`)."""

import io
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
import requests
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import Settings
from app.modules.whatsapp.application import publisher as pub
from app.modules.whatsapp.application.queue import goes_to_whatsapp, queue_whatsapp_post, to_jpeg
from app.modules.whatsapp.domain.models import WhatsAppPost
from app.modules.whatsapp.domain.text import channel_text
from app.modules.whatsapp.infrastructure.gateway_client import GatewayError, GatewayStatus, WhatsAppGatewayClient

NOW = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)  # 13:00 en Madrid
JID = "120363401234567890@newsletter"

POST = (
    "🍄 Webcam UGREEN 2K\n\n"
    "💶 29,99 € | -40 %\n\n"
    "💰 Ahorras 20 €\n\n"
    "🛒 https://amzn.to/abc\n\n"
    "⚠️ Finaliza el 30 de noviembre\n\n"
    "🔗 Todos los chollos en nuestra web\n\n"
    "#Webcams #Perifericos\n"
)


def _settings(**kw):
    base = dict(
        whatsapp_enabled=True, whatsapp_gateway_token="t" * 32, whatsapp_channel=JID,
        whatsapp_channels="main,admin", whatsapp_min_interval_minutes=20, whatsapp_daily_limit=15,
        telegram_main_channel_id="-100main", telegram_admin_channel_id="-100admin", telegram_enabled=True,
    )
    return Settings(**{**base, **kw})


def _jpeg(size=(800, 600), mode="RGB", fmt="JPEG") -> bytes:
    out = io.BytesIO()
    Image.new(mode, size, (200, 30, 30) if mode == "RGB" else (200, 30, 30, 128)).save(out, format=fmt)
    return out.getvalue()


@pytest.fixture(autouse=True)
def _clean_state():
    pub._resolved_jid.clear()
    pub._last_alert.clear()
    yield
    pub._resolved_jid.clear()
    pub._last_alert.clear()


# ── Texto ────────────────────────────────────────────────────────────────────

def test_texto_con_tarjeta_sin_lineas_de_precio_ni_hashtags():
    text = channel_text(POST, with_card=True)
    assert text.startswith("🔥 *Webcam UGREEN 2K*")
    assert "29,99" not in text and "Ahorras" not in text
    assert "👉 https://amzn.to/abc" in text
    assert "https://buenchollotech.com/whatsapp" in text
    assert "#Webcams" not in text


def test_texto_sin_tarjeta_conserva_el_precio():
    text = channel_text(POST, with_card=False)
    assert "🏷️ *29,99 € | -40 %*" in text and "💸 *Ahorras 20 €*" in text


def test_manda_el_texto_editado_en_el_panel():
    assert channel_text(POST, edited="Texto a mano 👉 https://x", with_card=True) == "Texto a mano 👉 https://x"


def test_to_jpeg_convierte_png_con_transparencia_y_limita_el_tamano():
    out = to_jpeg(_jpeg((3200, 1600), mode="RGBA", fmt="PNG"))
    with Image.open(io.BytesIO(out)) as img:
        assert img.format == "JPEG" and img.size == (1600, 800)
    assert to_jpeg(b"no es una imagen") is None and to_jpeg(None) is None


@pytest.mark.parametrize("channels, channel, expected", [
    ("main,admin", "-100main", True), ("main,admin", "-100admin", True),
    ("main", "-100admin", False), ("main", "-100otro", False), ("main", "", False),
])
def test_canales_que_cuentan(channels, channel, expected):
    assert goes_to_whatsapp(channel, _settings(whatsapp_channels=channels)) is expected


# ── Cola ─────────────────────────────────────────────────────────────────────

class _Nested:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _queue_session(existing=False):
    session = MagicMock()
    session.begin_nested.return_value = _Nested()
    session.add = MagicMock()
    session.flush = AsyncMock()
    result = MagicMock()
    result.first.return_value = ("x",) if existing else None
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.asyncio
async def test_encola_con_la_tarjeta_y_un_margen_aleatorio():
    session = _queue_session()
    ok = await queue_whatsapp_post(
        session, _settings(), deal_id="d1", telegram_text=POST, card=b"CARD", image_url="u", now=NOW
    )
    assert ok
    post = session.add.call_args.args[0]
    assert isinstance(post, WhatsAppPost)
    assert post.image == b"CARD" and post.deal_id == "d1" and "Ahorras" not in post.text
    assert timedelta(seconds=45) <= post.not_before - NOW <= timedelta(seconds=180)


@pytest.mark.asyncio
async def test_sin_tarjeta_usa_la_foto_original():
    session = _queue_session()
    ok = await queue_whatsapp_post(
        session, _settings(), deal_id=None, telegram_text=POST, card=None, image_url="u",
        download=lambda url: _jpeg(), now=NOW,
    )
    post = session.add.call_args.args[0]
    assert ok and post.image[:2] == b"\xff\xd8" and "29,99" in post.text


@pytest.mark.asyncio
async def test_no_repite_un_chollo_que_ya_esta_en_el_canal():
    session = _queue_session(existing=True)
    ok = await queue_whatsapp_post(session, _settings(), deal_id="d1", telegram_text=POST, card=b"C", image_url=None)
    assert ok is False and not session.add.called


@pytest.mark.asyncio
async def test_apagado_no_encola_y_un_fallo_nunca_lanza():
    assert await queue_whatsapp_post(
        _queue_session(), _settings(whatsapp_enabled=False), deal_id="d1", telegram_text=POST, card=b"C", image_url=None
    ) is False
    broken = _queue_session()
    broken.execute = AsyncMock(side_effect=RuntimeError("BD caída"))
    assert await queue_whatsapp_post(broken, _settings(), deal_id="d1", telegram_text=POST, card=b"C", image_url=None) is False


@pytest.mark.asyncio
@pytest.mark.parametrize("channel, enabled, queued", [
    ("-100main", True, True), ("-100admin", True, True), ("-100otro", True, False), ("-100main", False, False),
])
async def test_el_suscriptor_solo_encola_los_canales_de_whatsapp(monkeypatch, channel, enabled, queued):
    from app.core.events import DealPostPublished
    from app.modules.whatsapp.application import subscriber

    queue = AsyncMock(return_value=True)
    monkeypatch.setattr(subscriber, "queue_whatsapp_post", queue)
    monkeypatch.setattr(subscriber, "get_settings", lambda: _settings(whatsapp_enabled=enabled))

    await subscriber.on_deal_post_published(DealPostPublished(
        session="S", channel_id=channel, text=POST, deal_id="d1", card=b"C", image_url="u", whatsapp_text="editado",
    ))

    assert queue.await_count == (1 if queued else 0)
    if queued:
        args, kwargs = queue.await_args
        assert args[0] == "S" and kwargs["whatsapp_text"] == "editado" and kwargs["card"] == b"C"


# ── Cliente de la pasarela ───────────────────────────────────────────────────

def _response(status=200, body=None):
    response = MagicMock(status_code=status)
    response.json.return_value = body if body is not None else {}
    return response


def test_cliente_manda_el_token_en_cabecera_y_la_imagen_en_base64():
    http = MagicMock()
    http.post.return_value = _response(body={"ok": True, "id": "MSG1"})
    client = WhatsAppGatewayClient("http://gw:3000/", "secreto", http=http)

    assert client.send(JID, "hola", b"IMG", (1200, 800)) == "MSG1"

    url = http.post.call_args.args[0]
    kwargs = http.post.call_args.kwargs
    assert url == "http://gw:3000/send" and "secreto" not in url
    assert kwargs["headers"] == {"Authorization": "Bearer secreto"}
    assert kwargs["json"] == {"jid": JID, "text": "hola", "image_base64": "SU1H", "width": 1200, "height": 800}


@pytest.mark.parametrize("exc, unknown, offline", [
    (requests.ReadTimeout(), True, False),
    (requests.ConnectTimeout(), False, True),
    (requests.ConnectionError(), False, True),
])
def test_cliente_distingue_caida_de_resultado_desconocido(exc, unknown, offline):
    http = MagicMock()
    http.post.side_effect = exc
    with pytest.raises(GatewayError) as err:
        WhatsAppGatewayClient("http://gw", "secreto", http=http).send(JID, "hola")
    assert err.value.unknown is unknown and err.value.offline is offline
    assert "secreto" not in str(err.value)


def test_cliente_503_es_sin_conexion_y_500_o_400_son_intentos():
    http = MagicMock()
    http.post.return_value = _response(503, {"error": "WhatsApp no está conectado"})
    with pytest.raises(GatewayError) as err:
        WhatsAppGatewayClient("http://gw", "t", http=http).send(JID, "x")
    assert err.value.offline and "no está conectado" in str(err.value)
    http.post.return_value = _response(500, {"error": "subida rechazada"})
    with pytest.raises(GatewayError) as err:
        WhatsAppGatewayClient("http://gw", "t", http=http).send(JID, "x")
    assert not err.value.offline and err.value.status == 500
    http.post.return_value = _response(400, {"error": "falta text"})
    with pytest.raises(GatewayError) as err:
        WhatsAppGatewayClient("http://gw", "t", http=http).send(JID, "x")
    assert not err.value.offline and err.value.status == 400


# ── Job de publicación ───────────────────────────────────────────────────────

class _Repo:
    def __init__(self, posts=(), last=None, today=0):
        self.posts = list(posts)
        self.last = last
        self.today = today

    async def last_published_at(self):
        return self.last

    async def published_since(self, since):
        return self.today

    async def next_due(self, now):
        due = [p for p in self.posts if p.status == "pending" and (p.not_before is None or p.not_before <= now)]
        return due[0] if due else None


class _Session:
    def __init__(self):
        self.commit = AsyncMock()
        self.rollback = AsyncMock()


class _Client:
    def __init__(self, connection="open", role="OWNER", fail=None, pairing=None):
        self.connection = connection
        self.role = role
        self.fail = list(fail or [])
        self.pairing = pairing
        self.sent = []
        self.channel_calls = []

    def status(self):
        return GatewayStatus(connection=self.connection, pairing_code=self.pairing)

    def channel(self, *, jid=None, invite=None):
        self.channel_calls.append(jid or invite)
        return {"jid": JID, "name": "BuenCholloTech", "role": self.role}

    def send(self, jid, text, image=None, size=None):
        self.sent.append((jid, text, image, size))
        if self.fail:
            raise self.fail.pop(0)
        return "MSG1"


def _post(**kw):
    base = dict(
        id="p1", text="🔥 *Webcam*\n\nresto", image=_jpeg((1200, 800)), status="pending", attempts=0,
        created_at=NOW - timedelta(minutes=5), not_before=NOW - timedelta(minutes=3),
    )
    return WhatsAppPost(**{**base, **kw})


def _publisher(repo, client, settings=None):
    notices = []
    publisher = pub.WhatsAppPublisher(_Session(), repo, settings or _settings(), client=client, notify=notices.append)
    return publisher, notices


@pytest.mark.asyncio
async def test_publica_con_imagen_y_su_tamano():
    post = _post()
    client = _Client()
    publisher, notices = _publisher(_Repo([post]), client)

    assert await publisher.run(NOW) == 1

    jid, text, image, size = client.sent[0]
    assert jid == JID and text.startswith("🔥 *Webcam*") and image is not None and size == (1200, 800)
    assert post.status == "published" and post.message_id == "MSG1" and post.published_at == NOW
    assert post.image is None and notices == []


@pytest.mark.asyncio
async def test_respeta_el_intervalo_minimo_y_el_tope_diario():
    client = _Client()
    publisher, _ = _publisher(_Repo([_post()], last=NOW - timedelta(minutes=10)), client)
    assert await publisher.run(NOW) == 0

    publisher, _ = _publisher(_Repo([_post()], last=NOW - timedelta(minutes=25), today=15), client)
    assert await publisher.run(NOW) == 0

    publisher, _ = _publisher(_Repo([_post()], last=NOW - timedelta(minutes=25), today=14), client)
    assert await publisher.run(NOW) == 1
    assert len(client.sent) == 1


@pytest.mark.asyncio
async def test_una_sola_publicacion_por_paso():
    posts = [_post(id="p1"), _post(id="p2")]
    client = _Client()
    publisher, _ = _publisher(_Repo(posts), client)
    assert await publisher.run(NOW) == 1
    assert [p.status for p in posts] == ["published", "pending"]


@pytest.mark.asyncio
async def test_sin_cola_no_pregunta_a_la_pasarela():
    client = MagicMock()
    publisher, _ = _publisher(_Repo([]), client)
    assert await publisher.run(NOW) == 0
    client.status.assert_not_called()


@pytest.mark.asyncio
async def test_desvinculado_no_gasta_intentos_y_avisa_como_mucho_cada_6_horas():
    post = _post()
    client = _Client(connection="pairing", pairing="ABCD-EFGH")
    publisher, notices = _publisher(_Repo([post]), client)

    await publisher.run(NOW)
    await publisher.run(NOW + timedelta(minutes=1))
    assert post.status == "pending" and post.attempts == 0 and client.sent == []
    assert len(notices) == 1 and "ABCD-EFGH" in notices[0]

    await publisher.run(NOW + timedelta(hours=6, minutes=1))
    assert len(notices) == 2


@pytest.mark.asyncio
async def test_pasarela_caida_al_enviar_no_gasta_intentos():
    post = _post()
    client = _Client(fail=[GatewayError("no responde", offline=True)])
    publisher, notices = _publisher(_Repo([post]), client)
    assert await publisher.run(NOW) == 0
    assert post.attempts == 0 and post.status == "pending" and len(notices) == 1


@pytest.mark.asyncio
async def test_tras_dos_fallos_con_imagen_sale_solo_el_texto():
    post = _post()
    client = _Client(fail=[GatewayError("subida rechazada", status=500), GatewayError("subida rechazada", status=500)])
    publisher, _ = _publisher(_Repo([post]), client)

    await publisher.run(NOW)
    await publisher.run(NOW + timedelta(minutes=1))
    assert post.attempts == 2 and post.status == "pending"
    await publisher.run(NOW + timedelta(minutes=2))

    assert [s[2] is not None for s in client.sent] == [True, True, False]
    assert post.status == "published" and "solo con texto" in post.last_error


@pytest.mark.asyncio
async def test_al_quinto_fallo_se_descarta_y_avisa():
    post = _post(attempts=4, image=None)
    client = _Client(fail=[GatewayError("HTTP 400 falta text", status=400)])
    publisher, notices = _publisher(_Repo([post]), client)
    await publisher.run(NOW)
    assert post.status == "error" and len(notices) == 1 and "Webcam" in notices[0]


@pytest.mark.asyncio
async def test_sin_confirmacion_se_da_por_publicada_y_no_se_repite():
    post = _post()
    client = _Client(fail=[GatewayError("tiempo agotado", unknown=True)])
    publisher, notices = _publisher(_Repo([post]), client)
    assert await publisher.run(NOW) == 1
    assert post.status == "published" and "revisa el Canal" in notices[0]


@pytest.mark.asyncio
async def test_caducada_a_las_12_horas():
    post = _post(created_at=NOW - timedelta(hours=13))
    client = _Client()
    publisher, notices = _publisher(_Repo([post]), client)
    await publisher.run(NOW)
    assert post.status == "error" and post.image is None and client.sent == [] and len(notices) == 1


@pytest.mark.asyncio
async def test_resuelve_el_enlace_de_invitacion_una_vez():
    settings = _settings(whatsapp_channel="https://whatsapp.com/channel/0029VbD7ZIt4dTnQlrLmfs0Y")
    client = _Client()
    posts = [_post(id="p1"), _post(id="p2")]
    publisher, _ = _publisher(_Repo(posts), client, settings)
    await publisher.run(NOW)
    publisher, _ = _publisher(_Repo(posts), client, settings)
    await publisher.run(NOW + timedelta(minutes=30))
    assert client.channel_calls == ["0029VbD7ZIt4dTnQlrLmfs0Y"]
    assert [s[0] for s in client.sent] == [JID, JID]


@pytest.mark.asyncio
async def test_si_la_cuenta_no_administra_el_canal_no_publica_y_avisa():
    post = _post()
    client = _Client(role="SUBSCRIBER")
    publisher, notices = _publisher(_Repo([post]), client)
    assert await publisher.run(NOW) == 0
    assert client.sent == [] and post.attempts == 0 and "no administra" in notices[0]


@pytest.mark.asyncio
async def test_apagado_no_hace_nada():
    client = MagicMock()
    publisher, _ = _publisher(_Repo([_post()]), client, _settings(whatsapp_enabled=False))
    assert await publisher.run(NOW) == 0
    client.status.assert_not_called()


def test_el_dia_empieza_a_medianoche_de_madrid():
    assert pub.start_of_day(NOW) == datetime(2026, 11, 25, 23, 0, tzinfo=timezone.utc)


# ── Estado (admin) ───────────────────────────────────────────────────────────

def test_el_estado_exige_admin():
    from app.main import app

    response = TestClient(app).get("/v1/whatsapp/status")
    assert response.status_code in {401, 403}


# ── Resumen semanal y otras publicaciones (WhatsAppPostRequested) ────────────

@pytest.mark.asyncio
async def test_el_resumen_semanal_se_encola_con_su_collage_y_sin_quitar_precios(monkeypatch):
    from contextlib import asynccontextmanager

    from app.core.events import WhatsAppPostRequested
    from app.modules.whatsapp.application import subscriber

    session = MagicMock()
    session.commit = AsyncMock()

    @asynccontextmanager
    async def fake_job_session(settings):
        yield session

    queue = AsyncMock(return_value=True)
    monkeypatch.setattr(subscriber, "queue_whatsapp_post", queue)
    monkeypatch.setattr(subscriber, "job_session", fake_job_session)
    monkeypatch.setattr(subscriber, "get_settings", lambda: _settings(database_url="postgresql+asyncpg://x/y"))

    await subscriber.on_whatsapp_post_requested(
        WhatsAppPostRequested(telegram_text="TOP", whatsapp_text="*TOP*", image=b"COLLAGE")
    )

    kwargs = queue.await_args.kwargs
    assert kwargs["card"] == b"COLLAGE" and kwargs["whatsapp_text"] == "*TOP*" and kwargs["strip_prices"] is False
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_strip_prices_false_conserva_los_precios_aunque_haya_imagen():
    session = _queue_session()
    await queue_whatsapp_post(
        session, _settings(), deal_id=None, telegram_text=POST, card=b"COLLAGE", image_url=None,
        strip_prices=False, now=NOW,
    )
    assert "29,99" in session.add.call_args.args[0].text


@pytest.mark.asyncio
async def test_resumen_semanal_avisa_a_whatsapp_solo_si_esta_activo(monkeypatch):
    from app.core import events
    from app.modules.telegram.application.weekly_digest import announce_to_whatsapp

    seen = []

    async def fake_publish(event):
        seen.append(event)

    monkeypatch.setattr(events, "publish", fake_publish)
    service = MagicMock(last_image=b"IMG")
    digest = MagicMock(telegram_text="pie", full_text="completo", whatsapp_text="*wa*")

    await announce_to_whatsapp(service, digest, _settings(whatsapp_enabled=False))
    assert seen == []
    await announce_to_whatsapp(service, digest, _settings())
    assert seen[0].telegram_text == "completo" and seen[0].image == b"IMG" and seen[0].whatsapp_text == "*wa*"


# ── Sin copia «versión WhatsApp» al canal Admin con el Canal automático ──────

@pytest.mark.asyncio
async def test_programadas_sin_copia_al_admin(monkeypatch):
    from app.modules.scheduled_deals.application import publication_worker as pw

    copy = MagicMock()
    monkeypatch.setattr(pw, "send_whatsapp_copy", copy)
    worker = pw.ScheduledPublicationWorker(None, None, None, MagicMock(), "-100main", "-100admin", whatsapp_copy=False)
    await worker._send_whatsapp_copy(MagicMock(telegram_text="t", image_url=None))
    copy.assert_not_called()

    worker.whatsapp_copy = True
    await worker._send_whatsapp_copy(MagicMock(telegram_text="t", image_url=None))
    copy.assert_called_once()


def test_resumen_semanal_sin_copia_al_admin(monkeypatch):
    from app.modules.telegram.application import weekly_digest as wd

    copy = MagicMock()
    monkeypatch.setattr(wd, "send_whatsapp_copy", copy)
    bot = MagicMock()
    bot.send_photo_bytes.return_value = True
    service = wd.WeeklyDigestService(MagicMock(), bot, lambda t: [], "-100admin", "https://x", whatsapp_copy=False)
    monkeypatch.setattr(service, "collage", lambda digest: b"IMG")
    digest = MagicMock(telegram_text="pie", caption_fits=True)

    assert service.send(digest) is True
    copy.assert_not_called()
    assert service.last_image == b"IMG"


def test_las_factorias_apagan_la_copia_con_whatsapp_activo():
    from app.modules.scheduled_tasks.application.factory import build_reactivation_notifier
    from app.modules.telegram.application.weekly_digest import build_weekly_digest_service

    session = MagicMock()
    assert build_reactivation_notifier(session, _settings()).whatsapp_copy is False
    assert build_reactivation_notifier(session, _settings(whatsapp_enabled=False)).whatsapp_copy is True
    assert build_weekly_digest_service(session, _settings()).whatsapp_copy is False
