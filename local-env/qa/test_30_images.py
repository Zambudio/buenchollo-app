"""Subida de imágenes: archivo, URL externa y todo lo que puede ir mal."""

import io
import struct
import zlib

import pytest
from PIL import Image

from conftest import assert_no_5xx, detail

BUCKET_PREFIX = "/storage/v1/object/public/deal-images/submissions/"


def image_bytes(fmt: str, size=(800, 600), color=(200, 30, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format=fmt)
    return buf.getvalue()


def png_bomb(width: int, height: int) -> bytes:
    """PNG enorme en píxeles pero diminuto en bytes (todo ceros comprimidos)."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 1, 0, 0, 0, 0)
    row = b"\x00" + b"\x00" * ((width + 7) // 8)
    raw = zlib.compress(row * height, 9)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", raw) + chunk(b"IEND", b"")


def upload(pool, content: bytes, name="foto.png", ctype="image/png", field="file"):
    acc = pool.next("images")
    return acc, acc.post("/v1/submissions/images", files={field: (name, content, ctype)})


@pytest.mark.parametrize(
    "fmt,name,ctype",
    [("PNG", "a.png", "image/png"), ("JPEG", "b.jpg", "image/jpeg"), ("WEBP", "c.webp", "image/webp")],
)
def test_valid_upload_is_converted_to_webp_in_our_bucket(pool, fmt, name, ctype):
    acc, resp = upload(pool, image_bytes(fmt), name, ctype)
    assert resp.status_code == 200, detail(resp)
    data = resp.json()
    assert BUCKET_PREFIX + acc.id + "/" in data["url"]
    assert data["url"].endswith(".webp")
    assert data["width"] > 0 and data["height"] > 0


def test_wrong_extension_but_real_image_is_accepted(pool):
    """El tipo se decide por el contenido, no por el nombre ni el content-type."""
    _, resp = upload(pool, image_bytes("JPEG"), "captura.txt", "text/plain")
    assert resp.status_code == 200, detail(resp)


def test_very_large_dimensions_are_downscaled_or_rejected(pool):
    _, resp = upload(pool, image_bytes("JPEG", size=(6000, 4000)), "big.jpg", "image/jpeg")
    assert_no_5xx(resp)
    if resp.status_code == 200:
        assert max(resp.json()["width"], resp.json()["height"]) <= 4000


@pytest.mark.parametrize(
    "content,name,ctype",
    [
        (b"esto no es una imagen", "fake.png", "image/png"),
        (b"", "vacio.png", "image/png"),
        (b"<svg xmlns='http://www.w3.org/2000/svg' onload='alert(1)'><script>alert(1)</script></svg>",
         "xss.svg", "image/svg+xml"),
        (b"%PDF-1.4\n1 0 obj<<>>endobj", "doc.pdf", "application/pdf"),
        (b"GIF89a" + b"\x00" * 20, "roto.gif", "image/gif"),
        (image_bytes("PNG")[:200], "truncada.png", "image/png"),
    ],
)
def test_non_images_are_rejected_with_4xx(pool, content, name, ctype):
    _, resp = upload(pool, content, name, ctype)
    assert_no_5xx(resp)
    assert 400 <= resp.status_code < 500, detail(resp)


def test_decompression_bomb_is_rejected(pool):
    _, resp = upload(pool, png_bomb(30000, 30000), "bomba.png")
    assert_no_5xx(resp)
    assert 400 <= resp.status_code < 500, detail(resp)


def test_file_over_5mb_is_rejected(pool):
    """La API corta con 413 en cuanto pasa el límite; un cliente que siga enviando
    puede ver la conexión cerrada en vez del 413. La web lo comprueba antes de subir."""
    import httpx

    try:
        _, resp = upload(pool, b"\x89PNG\r\n\x1a\n" + b"\x00" * (6 * 1024 * 1024), "enorme.png")
    except (httpx.ReadError, httpx.RemoteProtocolError, httpx.WriteError):
        return
    assert_no_5xx(resp)
    assert resp.status_code in (400, 413, 422), detail(resp)


def test_missing_file_field_is_422(pool):
    _, resp = upload(pool, image_bytes("PNG"), field="imagen")
    assert resp.status_code == 422, detail(resp)


def test_tiny_image_does_not_crash(pool):
    _, resp = upload(pool, image_bytes("PNG", size=(1, 1)))
    assert_no_5xx(resp)


def test_transparent_and_grayscale_images_are_accepted(pool):
    for mode, color in (("RGBA", (0, 0, 0, 0)), ("L", 128), ("P", 3)):
        buf = io.BytesIO()
        Image.new(mode, (300, 300), color).save(buf, format="PNG")
        _, resp = upload(pool, buf.getvalue())
        assert resp.status_code == 200, f"{mode}: {detail(resp)}"


# ── Desde URL ──────────────────────────────────────────────────────────────


def from_url(pool, url):
    return pool.next("images-url").post("/v1/submissions/images/from-url", json={"url": url})


@pytest.fixture(scope="module")
def amazon_image_url(pool):
    resp = pool.next("check").post(
        "/v1/submissions/check-link", json={"url": "https://www.amazon.es/dp/B09B8X9RGM"}
    )
    prefill = resp.json().get("prefill") or {}
    if not prefill.get("image_url"):
        pytest.skip("Amazon no ha devuelto imagen en el prefill")
    return prefill["image_url"]


def test_amazon_image_url_is_ingested(pool, amazon_image_url):
    """Las imágenes del CDN de Amazon son de confianza: se aceptan sin re-subirlas."""
    resp = from_url(pool, amazon_image_url)
    assert resp.status_code == 200, detail(resp)
    url = resp.json()["url"]
    assert BUCKET_PREFIX in url or url.startswith("https://m.media-amazon.com/"), url


def test_public_image_from_other_site_is_ingested(pool):
    resp = from_url(pool, "https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png")
    assert_no_5xx(resp)
    assert resp.status_code == 200, detail(resp)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8000/health",
        "http://localhost:8025/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]:8000/",
        "http://10.0.0.1/imagen.jpg",
        "http://192.168.1.1/imagen.jpg",
        "file:///C:/Windows/win.ini",
        "gopher://127.0.0.1:6379/_INFO",
        "https://www.google.com/",
        "https://upload.wikimedia.org/no-existe-esta-imagen-qa.png",
        "no es una url",
        "https://0x7f000001/imagen.jpg",
        "https://2130706433/imagen.jpg",
        "http://127.1/imagen.jpg",
    ],
)
def test_bad_or_internal_image_urls_are_rejected(pool, url):
    resp = from_url(pool, url)
    assert_no_5xx(resp)
    assert 400 <= resp.status_code < 500, detail(resp)


def test_empty_url_is_422(pool):
    resp = from_url(pool, "")
    assert resp.status_code == 422, detail(resp)
