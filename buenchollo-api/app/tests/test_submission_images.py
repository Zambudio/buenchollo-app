"""Tests for secure image ingestion (Pillow -> WebP), fetcher and storage."""

import asyncio
import functools
import struct
import zlib
from io import BytesIO
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.rate_limit import limiter
from app.core.security import AuthenticatedUser, get_current_user
from app.main import app
from app.modules.submissions.api import schemas
from app.modules.submissions.api.dependencies import get_profile_repository
from app.modules.submissions.api.router import get_image_fetcher, get_image_storage
from app.modules.submissions.application.image_processing import process_image
from app.modules.submissions.domain.exceptions import (
    ImageStorageUnavailableError,
    InvalidImageError,
)
from app.modules.submissions.infrastructure import image_fetcher
from app.modules.submissions.infrastructure.image_fetcher import ImageFetcher
from app.modules.submissions.infrastructure.storage import SubmissionImageStorage



def run_async(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))

    return wrapper


URL = "/v1/submissions/images"
BUCKET = "https://proj.supabase.co/storage/v1/object/public/deal-images/submissions/"


def make_image(fmt="PNG", size=(3000, 2000), **save):
    out = BytesIO()
    Image.new("RGB", size, (200, 30, 30)).save(out, format=fmt, **save)
    return out.getvalue()


def decode(data: bytes) -> Image.Image:
    image = Image.open(BytesIO(data))
    image.load()
    return image


# -- process_image ---------------------------------------------------------


def test_png_grande_se_reduce_a_webp_1600():
    result = process_image(make_image("PNG", (3000, 2000)))
    image = decode(result.data)
    assert image.format == "WEBP"
    assert (result.width, result.height) == (1600, 1067)
    assert image.size == (1600, 1067)


def test_jpeg_con_orientacion_exif_se_rota_y_pierde_exif():
    exif = Image.Exif()
    exif[0x0112] = 6  # rotar 90 grados
    result = process_image(make_image("JPEG", (400, 200), exif=exif))
    image = decode(result.data)
    assert image.size == (200, 400)
    assert (result.width, result.height) == (200, 400)
    assert not image.getexif()


def test_png_con_transparencia_conserva_alfa():
    out = BytesIO()
    Image.new("RGBA", (50, 50), (0, 0, 0, 0)).save(out, format="PNG")
    assert decode(process_image(out.getvalue()).data).mode == "RGBA"


def test_gif_animado_usa_primer_frame():
    out = BytesIO()
    frames = [Image.new("RGB", (30, 20), c) for c in ("red", "blue")]
    frames[0].save(out, format="GIF", save_all=True, append_images=frames[1:])
    result = process_image(out.getvalue())
    assert (result.width, result.height) == (30, 20)


@pytest.mark.parametrize(
    "data",
    [
        b"<html><body>hola</body></html>",
        b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"></svg>',
        b"",
        b"\x89PNG\r\n\x1a\ntruncado",
    ],
)
def test_contenido_no_imagen_es_rechazado(data):
    with pytest.raises(InvalidImageError):
        process_image(data)


def test_formato_no_permitido_es_rechazado():
    out = BytesIO()
    Image.new("RGB", (10, 10)).save(out, format="BMP")
    with pytest.raises(InvalidImageError):
        process_image(out.getvalue())


def _png_header(width: int, height: int) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        crc = zlib.crc32(kind + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(b"\x00"))


def test_imagen_de_mas_de_40_megapixeles_es_rechazada():
    with pytest.raises(InvalidImageError) as exc:
        process_image(_png_header(20000, 20000))
    assert "demasiado grande" in str(exc.value)


# -- ImageFetcher ----------------------------------------------------------


@pytest.fixture
def public_dns(monkeypatch):
    monkeypatch.setattr(image_fetcher, "resolves_to_private_ip", lambda _u: False)


def fetcher(handler):
    return ImageFetcher(transport=httpx.MockTransport(handler))


@run_async
async def test_fetch_devuelve_bytes(public_dns):
    f = fetcher(lambda req: httpx.Response(200, content=b"abc"))
    assert await f.fetch("https://example.com/a.jpg") == b"abc"


@run_async
async def test_fetch_redirect_a_loopback_es_rechazado():
    calls = []

    def handler(req):
        calls.append(str(req.url))
        return httpx.Response(302, headers={"location": "http://127.0.0.1/"})

    with pytest.raises(InvalidImageError):
        await fetcher(handler).fetch("http://93.184.216.34/a.jpg")
    assert calls == ["http://93.184.216.34/a.jpg"]


@run_async
async def test_fetch_metadata_cloud_es_rechazado():
    def handler(req):
        raise AssertionError("no debe hacerse la peticion")

    with pytest.raises(InvalidImageError):
        await fetcher(handler).fetch("http://169.254.169.254/latest/meta-data/")


@run_async
async def test_fetch_respuesta_de_6mb_es_rechazada(public_dns):
    f = fetcher(lambda req: httpx.Response(200, content=b"0" * (6 * 1024 * 1024)))
    with pytest.raises(InvalidImageError) as exc:
        await f.fetch("https://example.com/a.jpg")
    assert "5 MB" in str(exc.value)


@run_async
async def test_fetch_corta_en_streaming_sin_content_length(public_dns):
    async def chunks():
        for _ in range(7):
            yield b"0" * (1024 * 1024)

    f = fetcher(lambda req: httpx.Response(200, content=chunks()))
    with pytest.raises(InvalidImageError):
        await f.fetch("https://example.com/a.jpg")


@run_async
async def test_fetch_demasiadas_redirecciones(public_dns):
    f = fetcher(lambda req: httpx.Response(302, headers={"location": "https://example.com/n"}))
    with pytest.raises(InvalidImageError):
        await f.fetch("https://example.com/a.jpg")


@run_async
async def test_fetch_sigue_redireccion_valida(public_dns):
    def handler(req):
        if req.url.path == "/a":
            return httpx.Response(302, headers={"location": "/b"})
        return httpx.Response(200, content=b"ok")

    assert await fetcher(handler).fetch("https://example.com/a") == b"ok"


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/a.jpg",
        "file:///etc/passwd",
        "https://user:pw@example.com/a.jpg",
        "https://example.com\\@evil.com/a.jpg",
        "https://example.com:8080/a.jpg",
        "https://example.com/a b.jpg",
    ],
)
@run_async
async def test_fetch_url_insegura_es_rechazada(public_dns, url):
    def handler(req):
        raise AssertionError("no debe hacerse la peticion")

    with pytest.raises(InvalidImageError):
        await fetcher(handler).fetch(url)


@run_async
async def test_fetch_estado_no_200_es_error(public_dns):
    with pytest.raises(InvalidImageError):
        await fetcher(lambda req: httpx.Response(404)).fetch("https://example.com/a.jpg")


@run_async
async def test_fetch_error_de_red_es_error_de_dominio(public_dns):
    def handler(req):
        raise httpx.ConnectError("boom")

    with pytest.raises(InvalidImageError):
        await fetcher(handler).fetch("https://example.com/a.jpg")


# -- Storage ---------------------------------------------------------------


class FakeBucket:
    def __init__(self, error=None):
        self.error, self.calls = error, []

    def upload(self, path, data, options):
        if self.error:
            raise self.error
        self.calls.append((path, data, options))


def fake_client(bucket):
    return SimpleNamespace(storage=SimpleNamespace(from_=lambda name: (bucket, name)[0]))


@run_async
async def test_storage_sube_con_ruta_y_cabeceras():
    bucket = FakeBucket()
    storage = SubmissionImageStorage(lambda: fake_client(bucket), "https://proj.supabase.co")
    url = await storage.upload("user-1", b"webp")
    path, data, options = bucket.calls[0]
    assert path.startswith("submissions/user-1/") and path.endswith(".webp")
    assert data == b"webp"
    assert options["content-type"] == "image/webp"
    assert options["cache-control"] == "31536000"
    assert url == f"https://proj.supabase.co/storage/v1/object/public/deal-images/{path}"


@run_async
async def test_storage_fallo_es_503_de_dominio():
    storage = SubmissionImageStorage(
        lambda: fake_client(FakeBucket(RuntimeError("secret detail"))), "https://proj.supabase.co"
    )
    with pytest.raises(ImageStorageUnavailableError) as exc:
        await storage.upload("user-1", b"x")
    assert exc.value.http_status == 503
    assert "secret" not in str(exc.value)


@pytest.mark.parametrize(
    "supabase_url",
    ["https://proj.supabase.co", "https://proj.supabase.co/", "https://proj.supabase.co/rest/v1/"],
)
@run_async
async def test_url_devuelta_pasa_is_allowed_image(monkeypatch, supabase_url):
    monkeypatch.setattr(schemas, "get_settings", lambda: SimpleNamespace(supabase_url=supabase_url))
    storage = SubmissionImageStorage(lambda: fake_client(FakeBucket()), supabase_url)
    url = await storage.upload("00000000-0000-0000-0000-000000000000", b"x")
    assert schemas.is_allowed_image(url)


# -- Endpoints -------------------------------------------------------------


class FakeStorage:
    def __init__(self):
        self.uploads = []

    async def upload(self, user_id, data):
        self.uploads.append((user_id, data))
        return BUCKET + f"{user_id}/x.webp"


class FakeProfileRepo:
    async def get_by_user_id(self, user_id):
        return SimpleNamespace(display_name="Pedro")


class ExplodingFetcher:
    async def fetch(self, url):
        raise AssertionError("no debe descargar")


@pytest.fixture
def storage(monkeypatch):
    limiter.reset()
    monkeypatch.setattr(
        schemas, "get_settings", lambda: SimpleNamespace(supabase_url="https://proj.supabase.co/")
    )
    s = FakeStorage()
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id="u1", email="a@b.c")
    app.dependency_overrides[get_profile_repository] = lambda: FakeProfileRepo()
    app.dependency_overrides[get_image_storage] = lambda: s
    app.dependency_overrides[get_image_fetcher] = lambda: ExplodingFetcher()
    yield s
    app.dependency_overrides.clear()


@pytest.fixture
def client(storage):
    return TestClient(app)


def test_subida_devuelve_url_y_dimensiones(client, storage):
    r = client.post(URL, files={"file": ("image.png", make_image("PNG", (3000, 2000)), "text/plain")})
    assert r.status_code == 200
    assert r.json() == {"url": BUCKET + "u1/x.webp", "width": 1600, "height": 1067}
    user_id, data = storage.uploads[0]
    assert user_id == "u1" and decode(data).format == "WEBP"


def test_subida_de_html_con_nombre_png_es_400(client, storage):
    r = client.post(URL, files={"file": ("image.png", b"<html></html>", "image/png")})
    assert r.status_code == 400
    assert storage.uploads == []


def test_subida_de_mas_de_5mb_es_400(client, storage):
    r = client.post(URL, files={"file": ("a.png", b"0" * (5 * 1024 * 1024 + 1), "image/png")})
    assert r.status_code == 400
    assert "5 MB" in r.json()["detail"]
    assert storage.uploads == []


def test_subida_sin_perfil_completo_es_403(client):
    class Empty:
        async def get_by_user_id(self, user_id):
            return None

    app.dependency_overrides[get_profile_repository] = lambda: Empty()
    r = client.post(URL, files={"file": ("a.png", make_image("PNG", (10, 10)), "image/png")})
    assert r.status_code == 403


def test_subida_con_fallo_de_storage_es_503(client):
    class Broken:
        async def upload(self, user_id, data):
            raise ImageStorageUnavailableError()

    app.dependency_overrides[get_image_storage] = lambda: Broken()
    r = client.post(URL, files={"file": ("a.png", make_image("PNG", (10, 10)), "image/png")})
    assert r.status_code == 503
    assert "Inténtalo" in r.json()["detail"]


def test_from_url_amazon_no_descarga(client, storage):
    amazon = "https://m.media-amazon.com/images/I/a.jpg"
    r = client.post(f"{URL}/from-url", json={"url": amazon})
    assert r.status_code == 200
    assert r.json() == {"url": amazon, "width": 0, "height": 0}
    assert storage.uploads == []


def test_from_url_http_amazon_se_rehospeda_y_no_se_devuelve_tal_cual(client, storage):
    class Fetcher:
        async def fetch(self, url):
            return make_image("PNG", (20, 10))

    app.dependency_overrides[get_image_fetcher] = lambda: Fetcher()
    r = client.post(f"{URL}/from-url", json={"url": "http://m.media-amazon.com/images/I/a.jpg"})
    assert r.status_code == 200
    assert r.json()["url"].startswith(BUCKET)
    assert len(storage.uploads) == 1


def test_from_url_externa_se_descarga_procesa_y_sube(client, storage):
    class Fetcher:
        async def fetch(self, url):
            assert url == "https://example.com/p.png"
            return make_image("PNG", (100, 50))

    app.dependency_overrides[get_image_fetcher] = lambda: Fetcher()
    r = client.post(f"{URL}/from-url", json={"url": "https://example.com/p.png"})
    assert r.status_code == 200
    assert (r.json()["width"], r.json()["height"]) == (100, 50)
    assert r.json()["url"].startswith(BUCKET)


def test_from_url_privada_es_400(client):
    app.dependency_overrides[get_image_fetcher] = lambda: ImageFetcher()
    r = client.post(f"{URL}/from-url", json={"url": "http://169.254.169.254/"})
    assert r.status_code == 400
