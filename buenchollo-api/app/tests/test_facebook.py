"""Facebook: texto adaptado, cola, cliente de la Graph API y job de publicación."""

import io
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
import requests
from PIL import Image

from app.core.config import Settings
from app.modules.facebook.application import publisher as pub
from app.modules.facebook.application.queue import goes_to_facebook, queue_facebook_post, to_jpeg
from app.modules.facebook.domain.models import POST_ERROR, POST_PENDING, POST_PUBLISHED, FacebookPost
from app.modules.facebook.domain.text import MAX_MESSAGE, SITE_LINE, to_facebook_text
from app.modules.facebook.infrastructure.graph_client import FacebookApiError, FacebookGraphClient, PageAccess

NOW = datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc)

POST = (
    "🍄 Webcam UGREEN 2K\n\n"
    "🛒 https://amzn.to/abc\n\n"
    "✏️ Buena webcam para videollamadas\n\n"
    "⚠️ Finaliza el 30 de noviembre\n\n"
    "🔗 Todos los chollos en nuestra web\n\n"
    "#Webcams #Perifericos\n"
)


def _settings(**kw):
    base = dict(
        facebook_enabled=True, facebook_access_token="EAAsistema", facebook_page_id="615", facebook_channels="main",
        telegram_main_channel_id="-100main", telegram_admin_channel_id="-100admin", telegram_enabled=True,
        facebook_hashtags="chollos webcams", facebook_disclosure="ℹ️ Enlace de afiliado.",
    )
    return Settings(**{**base, **kw})


def _jpeg(size=(800, 600), mode="RGB") -> bytes:
    out = io.BytesIO()
    Image.new(mode, size, (200, 30, 30)).save(out, format="PNG" if mode == "RGBA" else "JPEG")
    return out.getvalue()


# ── Texto ────────────────────────────────────────────────────────────────────

def test_texto_conserva_el_enlace_de_compra_y_anade_web_aviso_y_hashtags():
    text = to_facebook_text(POST, "chollos webcams", "ℹ️ Enlace de afiliado.")
    assert text.startswith(
        "🔥 Webcam UGREEN 2K\n\n🛒 https://amzn.to/abc\n\n📝 Buena webcam para videollamadas\n\n⏰ Finaliza el 30 de noviembre"
    )
    assert "🔗" not in text
    assert text.endswith(f"{SITE_LINE}\n\nℹ️ Enlace de afiliado.\n\n#Webcams #Perifericos #chollos")


def test_texto_sin_aviso_ni_hashtags_y_con_limite():
    assert to_facebook_text("🍄 X").endswith(f"🔥 X\n\n{SITE_LINE}")
    long = to_facebook_text("🍄 X\n\n✏️ " + "palabra " * 1000, "a")
    assert len(long) <= MAX_MESSAGE and long.endswith(f"{SITE_LINE}\n\n#a")


# ── Cola ─────────────────────────────────────────────────────────────────────

def test_to_jpeg_convierte_y_aplana_transparencias():
    with Image.open(io.BytesIO(to_jpeg(_jpeg((3000, 1000), mode="RGBA")))) as img:
        assert img.format == "JPEG" and img.size == (2048, 683)
    assert to_jpeg(b"no es imagen") is None and to_jpeg(None) is None


def test_canales():
    s = _settings()
    assert goes_to_facebook("-100main", s) and not goes_to_facebook("-100admin", s)
    both = _settings(facebook_channels="main, admin")
    assert goes_to_facebook("-100admin", both) and not goes_to_facebook("-100otro", both)
    assert not goes_to_facebook("-100main", _settings(telegram_main_channel_id=""))


class _Session:
    def __init__(self):
        self.added = []
        self.commits = 0
        self.rollbacks = 0

    @asynccontextmanager
    async def begin_nested(self):
        yield

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        pass

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_encola_con_la_tarjeta_o_la_foto():
    session = _Session()
    assert await queue_facebook_post(session, _settings(), deal_id="d1", telegram_text=POST, card=b"CARD", image_url="u")
    assert await queue_facebook_post(
        session, _settings(), deal_id=None, telegram_text=POST, card=None, image_url="u", download=lambda u: _jpeg()
    )
    card, photo = session.added
    assert (card.deal_id, card.image) == ("d1", b"CARD") and card.message.startswith("🔥 Webcam")
    assert photo.image[:2] == b"\xff\xd8"


@pytest.mark.asyncio
async def test_no_encola_si_esta_apagado_sin_imagen_o_si_falla():
    session = _Session()
    assert not await queue_facebook_post(
        session, _settings(facebook_enabled=False), deal_id=None, telegram_text=POST, card=b"C", image_url=None
    )
    assert not await queue_facebook_post(
        session, _settings(), deal_id=None, telegram_text=POST, card=None, image_url="u", download=lambda u: None
    )

    async def boom():
        raise RuntimeError("bd caída")

    session.flush = boom
    assert not await queue_facebook_post(session, _settings(), deal_id=None, telegram_text=POST, card=b"C", image_url=None)
    assert session.added == [] or all(isinstance(p, FacebookPost) for p in session.added)


# ── Cliente ──────────────────────────────────────────────────────────────────

class _Resp:
    def __init__(self, status, data):
        self.status_code = status
        self._data = data

    def json(self):
        return self._data


def test_cliente_pide_el_token_de_la_pagina_y_sube_la_foto():
    http = MagicMock()
    http.request.side_effect = [
        _Resp(200, {"name": "Buenchollo Tech", "access_token": "EAApagina", "id": "615"}),
        _Resp(200, {"id": "foto1", "post_id": "615_99"}),
    ]
    client = FacebookGraphClient("EAAsistema", http=http)
    page = client.page_access("615")
    assert page == PageAccess(name="Buenchollo Tech", access_token="EAApagina")
    assert client.publish_photo("615", page.access_token, b"JPG", "hola") == "615_99"

    (a1, k1), (a2, k2) = http.request.call_args_list
    assert a1 == ("GET", "https://graph.facebook.com/v23.0/615")
    assert k1["headers"] == {"Authorization": "Bearer EAAsistema"} and "EAAsistema" not in str(k1["params"])
    assert a2 == ("POST", "https://graph.facebook.com/v23.0/615/photos")
    assert k2["headers"] == {"Authorization": "Bearer EAApagina"}
    assert k2["data"] == {"message": "hola", "published": "true"}
    assert k2["files"]["source"][1] == b"JPG"


def test_cliente_sin_acceso_a_la_pagina_y_errores():
    http = MagicMock()
    http.request.return_value = _Resp(200, {"name": "X", "id": "615"})
    with pytest.raises(FacebookApiError) as err:
        FacebookGraphClient("t", http=http).page_access("615")
    assert err.value.token_invalid

    http.request.return_value = _Resp(400, {"error": {"message": "Invalid OAuth access token", "code": 190}})
    with pytest.raises(FacebookApiError) as err:
        FacebookGraphClient("t", http=http).page_access("615")
    assert err.value.token_invalid and not err.value.transient

    http.request.return_value = _Resp(503, {})
    with pytest.raises(FacebookApiError) as err:
        FacebookGraphClient("t", http=http).page_access("615")
    assert err.value.transient


def test_tiempo_agotado_al_publicar_es_resultado_desconocido():
    http = MagicMock()
    http.request.side_effect = requests.ReadTimeout("https://graph.facebook.com/...")
    with pytest.raises(FacebookApiError) as err:
        FacebookGraphClient("t", http=http).publish_photo("615", "p", b"x", "m")
    assert err.value.unknown and not err.value.transient
    with pytest.raises(FacebookApiError) as err:
        FacebookGraphClient("t", http=http).page_access("615")
    assert err.value.transient and not err.value.unknown


# ── Job ──────────────────────────────────────────────────────────────────────

class _Repo:
    def __init__(self, posts):
        self.posts = {p.id: p for p in posts}

    async def pending_ids(self, limit=10):
        return [p.id for p in self.posts.values() if p.status == POST_PENDING][:limit]

    async def lock_pending(self, post_id):
        post = self.posts.get(post_id)
        return post if post and post.status == POST_PENDING else None


def _post(**kw):
    base = dict(id="p1", message="🔥 Webcam\n\n🛒 https://a", image=b"JPG", status=POST_PENDING, attempts=0, created_at=NOW)
    return FacebookPost(**{**base, **kw})


class _Client:
    def __init__(self, *, page_error=None, publish=None):
        self.page_error = page_error
        self.publish = publish or (lambda *a: "615_1")
        self.published = []

    def __call__(self, token, version):
        assert token == "EAAsistema"
        return self

    def page_access(self, page_id):
        if self.page_error:
            raise self.page_error
        return PageAccess(name="Buenchollo Tech", access_token="EAApagina")

    def publish_photo(self, page_id, page_token, image, message):
        self.published.append((page_id, page_token, image, message))
        return self.publish(page_id, page_token, image, message)


def _publisher(posts, client, alerts):
    repo = _Repo(posts)
    return pub.FacebookPublisher(_Session(), repo, _settings(), client_factory=client, notify=alerts.append), repo


@pytest.fixture(autouse=True)
def _reset_alerts():
    pub._last_token_alert = None
    yield
    pub._last_token_alert = None


@pytest.mark.asyncio
async def test_job_publica_lo_pendiente():
    client, alerts = _Client(), []
    publisher, repo = _publisher([_post()], client, alerts)
    assert await publisher.run(NOW) == 1
    post = repo.posts["p1"]
    assert (post.status, post.post_id, post.image, post.published_at) == (POST_PUBLISHED, "615_1", None, NOW)
    assert client.published == [("615", "EAApagina", b"JPG", "🔥 Webcam\n\n🛒 https://a")]
    assert alerts == []


@pytest.mark.asyncio
async def test_job_sin_pendientes_no_llama_a_meta():
    client = _Client(page_error=AssertionError("no debería llamar"))
    publisher, _ = _publisher([], client, [])
    assert await publisher.run(NOW) == 0


@pytest.mark.asyncio
async def test_job_reintenta_y_acaba_en_error_con_aviso():
    def fail(*a):
        raise FacebookApiError("Error temporal", code=2, transient=True)

    alerts = []
    publisher, repo = _publisher([_post(attempts=4)], _Client(publish=fail), alerts)
    assert await publisher.run(NOW) == 0
    post = repo.posts["p1"]
    assert (post.status, post.attempts, post.image) == (POST_ERROR, 5, None)
    assert len(alerts) == 1 and "No se pudo publicar en Facebook" in alerts[0]


@pytest.mark.asyncio
async def test_job_descarta_las_caducadas():
    alerts = []
    publisher, repo = _publisher([_post(created_at=NOW - timedelta(hours=25))], _Client(), alerts)
    assert await publisher.run(NOW) == 0
    assert repo.posts["p1"].status == POST_ERROR and len(alerts) == 1


@pytest.mark.asyncio
async def test_job_sin_confirmacion_se_da_por_publicada():
    def timeout(*a):
        raise FacebookApiError("Facebook no respondió", unknown=True)

    alerts = []
    publisher, repo = _publisher([_post()], _Client(publish=timeout), alerts)
    assert await publisher.run(NOW) == 1
    assert repo.posts["p1"].status == POST_PUBLISHED and "revisa la página" in alerts[0]


@pytest.mark.asyncio
async def test_token_invalido_para_la_cola_y_avisa_como_mucho_cada_12_h():
    alerts = []
    client = _Client(page_error=FacebookApiError("Invalid OAuth access token", code=190))
    publisher, repo = _publisher([_post()], client, alerts)
    assert await publisher.run(NOW) == 0
    assert await publisher.run(NOW + timedelta(hours=1)) == 0
    assert repo.posts["p1"].status == POST_PENDING and len(alerts) == 1 and "FACEBOOK_ACCESS_TOKEN" in alerts[0]
    await publisher.run(NOW + timedelta(hours=13))
    assert len(alerts) == 2


@pytest.mark.asyncio
async def test_permiso_retirado_al_publicar_para_la_cola():
    def denied(*a):
        raise FacebookApiError("Requires pages_manage_posts", code=200)

    alerts = []
    client = _Client(publish=denied)
    publisher, repo = _publisher([_post(), _post(id="p2")], client, alerts)
    assert await publisher.run(NOW) == 0
    assert len(client.published) == 1 and repo.posts["p1"].attempts == 1 and len(alerts) == 1


@pytest.mark.asyncio
async def test_apagado_o_sin_configurar_no_hace_nada():
    client = _Client(page_error=AssertionError("no debería llamar"))
    for settings in (_settings(facebook_enabled=False), _settings(facebook_page_id=""), _settings(facebook_access_token="")):
        publisher = pub.FacebookPublisher(_Session(), _Repo([_post()]), settings, client_factory=client, notify=print)
        assert await publisher.run(NOW) == 0
