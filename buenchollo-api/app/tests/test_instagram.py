"""Instagram: texto adaptado, cola, cliente de la API y job de publicación."""

import io
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
import requests
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import Settings
from app.modules.instagram.application import publisher as pub
from app.modules.instagram.application.queue import fit_photo, is_main_channel, queue_instagram_post
from app.modules.instagram.domain.caption import BIO_LINE, MAX_CAPTION, to_instagram_caption
from app.modules.instagram.domain.models import InstagramAccount, InstagramPost
from app.modules.instagram.infrastructure.graph_client import InstagramApiError, InstagramGraphClient

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)

POST = (
    "🍄 Webcam UGREEN 2K\n\n"
    "🛒 https://amzn.to/abc\n\n"
    "✏️ Buena webcam para videollamadas https://otra.web/x\n\n"
    "⚠️ Finaliza el 30 de noviembre\n\n"
    "🔗 Todos los chollos en nuestra web\n\n"
    "#Webcams #Perifericos\n"
)


def _settings(**kw):
    base = dict(
        instagram_enabled=True, instagram_access_token="tok-1", telegram_main_channel_id="-100main", telegram_enabled=True,
        public_api_url="https://api.example.com", instagram_hashtags="chollos webcams",
    )
    return Settings(**{**base, **kw})


def _jpeg(size=(800, 600)) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", size, (200, 30, 30)).save(out, format="JPEG")
    return out.getvalue()


# ── Texto ────────────────────────────────────────────────────────────────────

def test_caption_sin_enlaces_con_bio_y_hashtags():
    caption = to_instagram_caption(POST, "chollos webcams")
    assert caption.startswith("🔥 Webcam UGREEN 2K\n\n📝 Buena webcam para videollamadas\n\n⏰ Finaliza el 30 de noviembre")
    assert "http" not in caption and "🛒" not in caption and "nuestra web" not in caption
    assert BIO_LINE in caption
    # Los de categoría se conservan; los fijos se añaden sin repetir (sin distinguir mayúsculas).
    assert caption.endswith("#Webcams #Perifericos #chollos")


def test_caption_con_lineas_de_precio_si_no_hubo_tarjeta():
    caption = to_instagram_caption("🍄 X\n\n💶 Precio: 9,99 €\n💰 Ahorro: 5,00 € | -33 %\n\n🛒 https://a/b")
    assert "🏷️ Precio: 9,99 €\n💸 Ahorro: 5,00 € | -33 %" in caption


def test_caption_no_pasa_del_limite():
    caption = to_instagram_caption("🍄 X\n\n✏️ " + "palabra " * 600, "#a")
    assert len(caption) <= MAX_CAPTION
    assert caption.endswith(f"{BIO_LINE}\n\n#a")


# ── Cola ─────────────────────────────────────────────────────────────────────

def test_fit_photo_centra_en_1200x800():
    with Image.open(io.BytesIO(fit_photo(_jpeg((500, 1500))))) as img:
        assert (img.format, img.size) == ("JPEG", (1200, 800))
    assert fit_photo(b"no es imagen") is None
    assert fit_photo(None) is None


def test_solo_el_canal_principal():
    s = _settings()
    assert is_main_channel("-100main", s)
    assert not is_main_channel("-100admin", s)
    assert not is_main_channel("-100main", _settings(telegram_main_channel_id=""))


class _Session:
    def __init__(self):
        self.added = []

    @asynccontextmanager
    async def begin_nested(self):
        yield

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        pass


@pytest.mark.asyncio
async def test_encola_con_la_tarjeta():
    session = _Session()
    ok = await queue_instagram_post(
        session, _settings(), deal_id="d1", telegram_text=POST, card=b"CARD", image_url="u", download=None
    )
    assert ok
    (post,) = session.added
    assert (post.deal_id, post.image) == ("d1", b"CARD")
    assert post.caption.startswith("🔥 Webcam")


@pytest.mark.asyncio
async def test_sin_tarjeta_usa_la_foto_original_encajada():
    session = _Session()
    ok = await queue_instagram_post(
        session, _settings(), deal_id=None, telegram_text=POST, card=None, image_url="u", download=lambda u: _jpeg()
    )
    assert ok
    with Image.open(io.BytesIO(session.added[0].image)) as img:
        assert img.size == (1200, 800)


@pytest.mark.asyncio
async def test_no_encola_si_esta_apagado_o_sin_imagen():
    session = _Session()
    assert not await queue_instagram_post(
        session, _settings(instagram_enabled=False), deal_id=None, telegram_text=POST, card=b"C", image_url=None
    )
    assert not await queue_instagram_post(
        session, _settings(), deal_id=None, telegram_text=POST, card=None, image_url="u", download=lambda u: None
    )
    assert session.added == []


@pytest.mark.asyncio
async def test_un_fallo_al_encolar_nunca_lanza():
    session = _Session()

    async def boom():
        raise RuntimeError("bd caída")

    session.flush = boom
    assert not await queue_instagram_post(session, _settings(), deal_id=None, telegram_text=POST, card=b"C", image_url=None)


# ── Cliente de la API ────────────────────────────────────────────────────────

class _Resp:
    def __init__(self, status, data):
        self.status_code = status
        self._data = data

    def json(self):
        return self._data


def test_cliente_manda_el_token_en_cabecera_y_no_en_la_url():
    http = MagicMock()
    http.request.return_value = _Resp(200, {"id": "c1"})
    InstagramGraphClient("secreto", http=http).create_image_container("u1", "https://img", "texto")
    args, kwargs = http.request.call_args
    assert args == ("POST", "https://graph.instagram.com/v23.0/u1/media")
    assert kwargs["headers"] == {"Authorization": "Bearer secreto"}
    assert "secreto" not in str(kwargs["params"]) and kwargs["json"] == {"image_url": "https://img", "caption": "texto"}


def test_cliente_interpreta_errores_de_meta():
    http = MagicMock()
    http.request.return_value = _Resp(400, {"error": {"message": "Invalid OAuth access token", "code": 190}})
    with pytest.raises(InstagramApiError) as err:
        InstagramGraphClient("t", http=http).me()
    assert err.value.token_invalid and not err.value.transient

    http.request.return_value = _Resp(500, {})
    with pytest.raises(InstagramApiError) as err:
        InstagramGraphClient("t", http=http).me()
    assert err.value.transient


def test_tiempo_agotado_al_publicar_es_resultado_desconocido():
    http = MagicMock()
    http.request.side_effect = requests.ReadTimeout("https://graph.instagram.com/...")
    with pytest.raises(InstagramApiError) as err:
        InstagramGraphClient("t", http=http).publish("u1", "c1")
    assert err.value.unknown and not err.value.transient
    with pytest.raises(InstagramApiError) as err:
        InstagramGraphClient("t", http=http).create_image_container("u1", "i", "c")
    assert err.value.transient and not err.value.unknown


def test_renovar_el_token_no_filtra_el_token_en_el_error():
    http = MagicMock()
    http.get.side_effect = requests.ConnectionError("https://graph.instagram.com/refresh_access_token?access_token=secreto")
    with pytest.raises(InstagramApiError) as err:
        InstagramGraphClient("secreto", http=http).refresh_token()
    assert "secreto" not in str(err.value)


# ── Job de publicación ───────────────────────────────────────────────────────

class _Repo:
    def __init__(self, posts=(), account=None):
        self.posts = {p.id: p for p in posts}
        self.acc = account

    async def account(self, for_update=False):
        return self.acc

    async def save_account(self, account):
        self.acc = account
        return account

    async def pending_ids(self, limit=10):
        return [p.id for p in self.posts.values() if p.status == "pending"][:limit]

    async def lock_pending(self, post_id):
        post = self.posts.get(post_id)
        return post if post and post.status == "pending" else None


class _JobSession:
    commit = AsyncMock()
    rollback = AsyncMock()


class _Client:
    def __init__(self, statuses=("FINISHED",), fail=None):
        self.calls = []
        self.statuses = list(statuses)
        self.fail = fail or {}

    def _maybe_fail(self, name):
        if name in self.fail:
            raise self.fail[name]

    def me(self):
        self.calls.append("me")
        self._maybe_fail("me")
        return {"user_id": "178", "username": "buenchollotech"}

    def create_image_container(self, user_id, image_url, caption):
        self.calls.append(("create", user_id, image_url))
        self._maybe_fail("create")
        return "c1"

    def container_status(self, container_id):
        self.calls.append("status")
        return self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]

    def publish(self, user_id, container_id):
        self.calls.append(("publish", container_id))
        self._maybe_fail("publish")
        return "m1"

    def refresh_token(self):
        self.calls.append("refresh")
        self._maybe_fail("refresh")
        from app.modules.instagram.infrastructure.graph_client import RefreshedToken

        return RefreshedToken("tok-2", 5_184_000)


def _post(**kw):
    base = dict(id="p1", caption="🔥 Webcam\n\nresto", image=b"IMG", status="pending", attempts=0, created_at=NOW)
    return InstagramPost(**{**base, **kw})


def _account(**kw):
    base = dict(
        id=1, access_token="tok-1", seed_hash=pub._hash("tok-1"), user_id="178", username="bct",
        refreshed_at=NOW - timedelta(days=1),
    )
    return InstagramAccount(**{**base, **kw})


def _publisher(repo, client, settings=None):
    notices = []
    publisher = pub.InstagramPublisher(
        _JobSession(), repo, settings or _settings(), client_factory=lambda token, version: client,
        notify=notices.append,
    )
    return publisher, notices


@pytest.mark.asyncio
async def test_siembra_la_cuenta_y_publica():
    post = _post()
    repo, client = _Repo([post]), _Client()
    publisher, notices = _publisher(repo, client)

    assert await publisher.run(NOW) == 1
    assert (repo.acc.user_id, repo.acc.username, repo.acc.access_token) == ("178", "buenchollotech", "tok-1")
    assert client.calls == ["me", ("create", "178", "https://api.example.com/v1/instagram/media/p1.jpg"), "status", ("publish", "c1")]
    assert (post.status, post.media_id, post.image, post.published_at) == ("published", "m1", None, NOW)
    assert notices == []


@pytest.mark.asyncio
async def test_si_instagram_aun_procesa_espera_al_siguiente_paso():
    post = _post()
    repo, client = _Repo([post], _account()), _Client(statuses=("IN_PROGRESS",))
    publisher, _ = _publisher(repo, client)

    assert await publisher.run(NOW) == 0
    assert (post.status, post.container_id) == ("pending", "c1")

    client.statuses = ["FINISHED"]
    assert await publisher.run(NOW) == 1
    assert post.status == "published"
    assert sum(1 for c in client.calls if isinstance(c, tuple) and c[0] == "create") == 1


@pytest.mark.asyncio
async def test_reintenta_y_al_quinto_fallo_avisa():
    post = _post()
    repo = _Repo([post], _account())
    client = _Client(fail={"create": InstagramApiError("Media download failed", code=9004)})
    publisher, notices = _publisher(repo, client)

    for _ in range(pub.MAX_ATTEMPTS):
        await publisher.run(NOW)
    assert (post.status, post.attempts) == ("error", 5)
    assert len(notices) == 1 and "Webcam" in notices[0] and "Media download failed" in notices[0]


@pytest.mark.asyncio
async def test_caducada_a_las_24_horas():
    post = _post(created_at=NOW - timedelta(hours=25))
    repo = _Repo([post], _account())
    publisher, notices = _publisher(repo, _Client())

    assert await publisher.run(NOW) == 0
    assert post.status == "error" and len(notices) == 1


@pytest.mark.asyncio
async def test_sin_confirmacion_al_publicar_no_se_repite():
    post = _post()
    repo = _Repo([post], _account())
    publisher, notices = _publisher(repo, _Client(fail={"publish": InstagramApiError("timeout", unknown=True)}))

    assert await publisher.run(NOW) == 1
    assert post.status == "published" and post.media_id is None
    assert len(notices) == 1 and "revisa el feed" in notices[0]


@pytest.mark.asyncio
async def test_token_invalido_para_la_cola_y_avisa_una_vez():
    posts = [_post(id="p1"), _post(id="p2")]
    repo = _Repo(posts, _account())
    client = _Client(fail={"create": InstagramApiError("Invalid OAuth", code=190)})
    publisher, notices = _publisher(repo, client)

    await publisher.run(NOW)
    await publisher.run(NOW + timedelta(minutes=2))
    assert [p.attempts for p in posts] == [2, 0]  # se para en la primera
    assert len(notices) == 1 and "INSTAGRAM_ACCESS_TOKEN" in notices[0]
    assert repo.acc.last_error == "Invalid OAuth"


@pytest.mark.asyncio
async def test_renueva_el_token_cada_semana():
    repo = _Repo([], _account(refreshed_at=NOW - timedelta(days=8)))
    client = _Client()
    publisher, _ = _publisher(repo, client)

    await publisher.run(NOW)
    assert client.calls == ["refresh"]
    assert (repo.acc.access_token, repo.acc.refreshed_at) == ("tok-2", NOW)
    assert repo.acc.expires_at == NOW + timedelta(days=60)
    # El hash sigue siendo el del token del .env: no se vuelve a sembrar.
    await publisher.run(NOW + timedelta(minutes=2))
    assert repo.acc.access_token == "tok-2"


@pytest.mark.asyncio
async def test_si_falla_la_renovacion_se_reintenta_en_6_horas_y_sigue_publicando():
    post = _post()
    repo = _Repo([post], _account(refreshed_at=NOW - timedelta(days=8)))
    publisher, _ = _publisher(repo, _Client(fail={"refresh": InstagramApiError("caída", transient=True)}))

    assert await publisher.run(NOW) == 1
    assert repo.acc.refreshed_at == NOW - pub.REFRESH_EVERY + timedelta(hours=6)


@pytest.mark.asyncio
async def test_un_token_nuevo_en_el_env_sustituye_al_guardado():
    repo = _Repo([], _account(access_token="tok-viejo", seed_hash=pub._hash("tok-viejo")))
    client = _Client()
    publisher, _ = _publisher(repo, client, _settings(instagram_access_token="tok-nuevo"))

    await publisher.run(NOW)
    assert repo.acc.access_token == "tok-nuevo" and client.calls == ["me"]


@pytest.mark.asyncio
async def test_apagado_no_hace_nada():
    repo, client = _Repo([_post()]), _Client()
    publisher, _ = _publisher(repo, client, _settings(instagram_enabled=False))
    assert await publisher.run(NOW) == 0 and client.calls == []


# ── Imagen pública para Instagram ────────────────────────────────────────────

def test_la_imagen_solo_se_sirve_si_esta_pendiente(monkeypatch):
    from app.core.database import get_db
    from app.main import app

    async def fake_db():
        yield MagicMock()

    images = {"3f0c8f8e-4a59-4b38-9a6a-0d6f1f0f6c11": b"JPEG"}

    async def pending_image(self, post_id, created_after):
        return images.get(post_id)

    monkeypatch.setattr(
        "app.modules.instagram.infrastructure.repository.InstagramRepository.pending_image", pending_image
    )
    app.dependency_overrides[get_db] = fake_db
    try:
        client = TestClient(app)
        ok = client.get("/v1/instagram/media/3f0c8f8e-4a59-4b38-9a6a-0d6f1f0f6c11.jpg")
        assert (ok.status_code, ok.headers["content-type"], ok.content) == (200, "image/jpeg", b"JPEG")
        assert ok.headers["cache-control"] == "no-store"
        assert client.get("/v1/instagram/media/9a0c8f8e-4a59-4b38-9a6a-0d6f1f0f6c11.jpg").status_code == 404
        assert client.get("/v1/instagram/media/no-uuid.jpg").status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_el_estado_exige_admin():
    from app.main import app

    assert TestClient(app).get("/v1/instagram/status").status_code in (401, 403)
