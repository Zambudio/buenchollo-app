"""Adaptadores Awin / Tradedoubler con transporte HTTP simulado (FIXTURES:
ninguna llamada sale a Internet; nada de esto valida la integración en vivo)."""

import gzip
import io
import json
import zipfile
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from app.core.config import Settings
from app.modules.affiliates.infrastructure.awin_client import (
    ALLOWED_HOSTS as AWIN_HOSTS,
    AwinClient,
    AwinLinkUnavailable,
    iter_feed_rows,
    parse_feed_list,
)
from app.modules.affiliates.infrastructure.http import (
    MinuteRateLimiter,
    NetworkAuthError,
    NetworkError,
    NetworkHostNotAllowed,
    NetworkRateLimited,
    SafeHttp,
    redact,
)
from app.modules.affiliates.infrastructure.tradedoubler_client import (
    ALLOWED_HOSTS as TD_HOSTS,
    TradedoublerClient,
    map_td_product,
)

FIX = Path(__file__).parent / "fixtures" / "affiliates"
TOKEN = "awin-token-FIXTURE-0123456789"
FEED_KEY = "FIXTUREKEY123456"
TD_TOKEN = "a" * 40


def _settings(**kw):
    base = dict(
        awin_publisher_id="3148595",
        awin_access_token=TOKEN,
        awin_feed_api_key=FEED_KEY,
        tradedoubler_products_token=TD_TOKEN,
        tradedoubler_site_id="123456",
    )
    base.update(kw)
    return Settings(**base)


def _awin(handler, **kw):
    s = _settings(**kw)
    http = SafeHttp(AWIN_HOSTS, secrets=(TOKEN, FEED_KEY), transport=httpx.MockTransport(handler), backoff_seconds=0)
    return AwinClient(s, http=http)


def _td(handler):
    http = SafeHttp(TD_HOSTS, secrets=(TD_TOKEN,), transport=httpx.MockTransport(handler), backoff_seconds=0)
    return TradedoublerClient(_settings(), http=http)


# ── Awin Link Builder ────────────────────────────────────────────────────────

def test_linkbuilder_solicita_y_prefiere_enlace_corto():
    def handler(request):
        assert json.loads(request.content)["shorten"] is True
        return httpx.Response(200, json={"url": "https://www.awin1.com/long", "shortUrl": "https://tidd.ly/example"})

    assert _awin(handler).generate_link("20982", "https://www.pccomponentes.com/x") == "https://tidd.ly/example"


def test_linkbuilder_envia_destino_y_auth_bearer():
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"url": "https://www.awin1.com/cread.php?awinmid=20982&awinaffid=3148595&ued=x"})

    url = _awin(handler).generate_link("20982", "https://www.pccomponentes.com/x?color=negro", "bct")
    assert url.startswith("https://www.awin1.com/")
    assert seen["url"] == "https://api.awin.com/publishers/3148595/linkbuilder/generate"
    assert seen["auth"] == f"Bearer {TOKEN}"
    assert seen["body"]["advertiserId"] == 20982
    assert seen["body"]["destinationUrl"] == "https://www.pccomponentes.com/x?color=negro"
    assert seen["body"]["parameters"] == {"clickref": "bct"}


def test_linkbuilder_error_no_fabrica_enlace():
    handler = lambda r: httpx.Response(200, json={"description": "Unknown error! Please try again later!"})  # noqa: E731
    with pytest.raises(AwinLinkUnavailable) as exc:
        _awin(handler).generate_link("20982", "https://www.pccomponentes.com/x")
    assert "Unknown error" in str(exc.value)


def test_linkbuilder_rechaza_dominio_inesperado_en_respuesta():
    handler = lambda r: httpx.Response(200, json={"url": "https://evil.example.com/?awinmid=1"})  # noqa: E731
    with pytest.raises(AwinLinkUnavailable):
        _awin(handler).generate_link("20982", "https://www.pccomponentes.com/x")


def test_429_y_401_dan_estados_utiles_sin_reintentar():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(429)

    with pytest.raises(NetworkRateLimited):
        _awin(handler).generate_link("20982", "https://www.pccomponentes.com/x")
    assert len(calls) == 1
    with pytest.raises(NetworkAuthError):
        _awin(lambda r: httpx.Response(401)).generate_link("20982", "https://www.pccomponentes.com/x")


def test_5xx_reintenta_acotado():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503, json={})

    with pytest.raises(AwinLinkUnavailable):
        _awin(handler).generate_link("20982", "https://www.pccomponentes.com/x")
    assert len(calls) == 3  # 1 + 2 reintentos


def test_redireccion_a_host_interno_se_rechaza():
    def handler(request):
        return httpx.Response(302, headers={"location": "https://169.254.169.254/latest/meta-data"})

    with pytest.raises(NetworkHostNotAllowed):
        _awin(handler).generate_link("20982", "https://www.pccomponentes.com/x")


def test_limitador_por_minuto():
    limiter = MinuteRateLimiter(2)
    limiter.acquire()
    limiter.acquire()
    with pytest.raises(NetworkRateLimited):
        limiter.acquire()


def test_redaccion_de_secretos():
    msg = f"GET https://productdata.awin.com/datafeed/download/apikey/{FEED_KEY}/fid/1 Bearer {TOKEN} token={TD_TOKEN}"
    out = redact(msg, (TOKEN, FEED_KEY, TD_TOKEN))
    assert FEED_KEY not in out and TOKEN not in out and TD_TOKEN not in out
    list_url = f"https://ui.awin.com/productdata-darwin-download/publisher/3148595/{FEED_KEY}/1/feedList"
    assert FEED_KEY not in redact(list_url)


def test_programmes_por_relacion():
    def handler(request):
        rel = request.url.params["relationship"]
        assert request.url.params["countryCode"] == "ES"
        data = {"joined": [{"id": 20982}], "pending": [{"id": 124624}], "suspended": [], "rejected": []}[rel]
        return httpx.Response(200, json=data)

    assert _awin(handler).programmes_by_relationship() == {"20982": "joined", "124624": "pending"}


# ── Awin feeds ───────────────────────────────────────────────────────────────

def test_lista_de_feeds_fixture():
    rows = parse_feed_list((FIX / "awin_feed_list.csv").read_text(encoding="utf-8"))
    assert [r["feed_id"] for r in rows] == ["90001", "90002"]
    assert rows[0]["advertiser_id"] == "20982"
    assert rows[0]["last_imported"] == "2026-11-08 03:00:00"


def _gz(tmp_path, content: bytes) -> Path:
    path = tmp_path / "feed.gz"
    path.write_bytes(gzip.compress(content))
    return path


def test_feed_gzip_mapea_y_no_inventa(tmp_path):
    path = _gz(tmp_path, (FIX / "awin_feed.csv").read_bytes())
    rows = list(iter_feed_rows(path, 10_000_000, 1000))
    by_key = {r["product_key"]: r for r in rows}
    assert set(by_key) == {"F-1001", "F-2001", "F-2002", "F-3001"}  # la fila sin id se descarta

    monitor = by_key["F-1001"]
    assert monitor["price"] == Decimal("199.90")
    assert monitor["rrp_price"] == Decimal("279.00")
    assert monitor["in_stock"] is True
    assert "<script>" not in monitor["description"] and "alert" not in monitor["description"]
    assert monitor["normalized_url"] == "https://pccomponentes.com/fixture-monitor-27-qhd"

    ssd = by_key["F-2001"]
    assert ssd["delivery_cost"] is None and ssd["in_stock"] is True and ssd["rrp_price"] is None

    hub = by_key["F-3001"]
    assert hub["merchant_url"] is None  # javascript: rechazado
    assert hub["image_url"] is None  # http sin TLS rechazado
    assert hub["in_stock"] is None and hub["provider_updated_at"] is None
    assert hub["price"] == Decimal("12.50")


def test_feed_zip_y_bomba_de_descompresion(tmp_path):
    content = (FIX / "awin_feed.csv").read_bytes()
    zpath = tmp_path / "feed.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("feed.csv", content)
    assert len(list(iter_feed_rows(zpath, 10_000_000, 1000))) == 4

    bomb = _gz(tmp_path, b"aw_product_id,product_name\n" + b"x" * 5_000_000)
    with pytest.raises(NetworkError):
        list(iter_feed_rows(bomb, 1_000_000, 1000))


def test_feed_limite_de_filas(tmp_path):
    path = _gz(tmp_path, (FIX / "awin_feed.csv").read_bytes())
    with pytest.raises(NetworkError):
        list(iter_feed_rows(path, 10_000_000, 2))


def test_descarga_con_tope_de_tamano(tmp_path):
    big = b"x" * 3_000_000
    client = _awin(lambda r: httpx.Response(200, content=big), awin_feed_max_download_mb=1)
    with pytest.raises(NetworkError):
        client.download_feed("https://productdata.awin.com/datafeed/download/apikey/K/fid/1/", tmp_path / "f")


def test_descarga_fuera_de_allowlist(tmp_path):
    client = _awin(lambda r: httpx.Response(200, content=b"ok"))
    with pytest.raises(NetworkHostNotAllowed):
        client.download_feed("https://evil.example.com/feed.gz", tmp_path / "f")
    with pytest.raises(NetworkHostNotAllowed):
        client.download_feed("http://productdata.awin.com/feed.gz", tmp_path / "f")


# ── Tradedoubler ─────────────────────────────────────────────────────────────

def test_td_busqueda_usa_parametros_matrix_codificados():
    seen = {}

    def handler(request):
        seen["path"] = request.url.raw_path.decode()
        seen["token"] = request.url.params["token"]
        return httpx.Response(200, json=json.loads((FIX / "td_products.json").read_text(encoding="utf-8")))

    items = _td(handler).search_products("55501", ean="8400000000031", query="portatil;fid=1/../x")
    assert len(items) == 2
    assert seen["path"].startswith("/1.0/products.json;fid=55501;ean=8400000000031;q=portatil%3Bfid%3D1%2F..%2Fx")
    assert seen["token"] == TD_TOKEN


def test_td_mapeo_fixture():
    data = json.loads((FIX / "td_products.json").read_text(encoding="utf-8"))
    mapped = map_td_product(data["products"][0], "55501")
    assert mapped["product_key"] == "TDOFFER-77"
    assert mapped["price"] == Decimal("699.00")
    assert mapped["tracking_url"].startswith("https://pdt.tradedoubler.com/")
    assert mapped["merchant_url"] == "https://www.mediamarkt.es/es/product/_fixture-portatil-15-77.html"
    assert mapped["ean"] == "8400000000031"
    assert mapped["in_stock"] is True
    assert mapped["description"] == "FIXTURE Portátil de 15,6 pulgadas."
    # Sin oferta del feed pedido → no se mapea.
    assert map_td_product(data["products"][0], "99999") is None
    # Producto sin disponibilidad ni envío: quedan None.
    other = map_td_product(data["products"][1], "55501")
    assert other["in_stock"] is None and other["shipping"] is None and other["image_url"] is None


def test_td_token_invalido():
    with pytest.raises(NetworkAuthError):
        _td(lambda r: httpx.Response(403, json={"code": 2})).search_products("1", query="x")


def test_td_respuesta_maliciosa_no_rompe():
    handler = lambda r: httpx.Response(200, content=b"<html>not json</html>")  # noqa: E731
    with pytest.raises(NetworkError):
        _td(handler).search_products("1", query="x")
    handler2 = lambda r: httpx.Response(200, json={"products": ["x", 1, None, {"name": "<script>x</script>"}]})  # noqa: E731
    items = _td(handler2).search_products("1", query="x")
    assert len(items) == 1 and map_td_product(items[0], "1") is None


def test_td_requests_original_url_and_history():
    def handler(request):
        assert ";sourceproducturl=true" in str(request.url)
        assert ";priceHistory=true" in str(request.url)
        return httpx.Response(200, json={"products": []})
    assert _td(handler).search_products("123") == []


def test_td_zero_shipping_is_preserved():
    data = json.loads((FIX / "td_products.json").read_text(encoding="utf-8"))["products"][0]
    data["offers"][0]["shippingCost"] = 0
    assert map_td_product(data, "55501")["shipping"] == "0"


def test_unselected_or_unavailable_feeds_not_searchable():
    from types import SimpleNamespace
    from app.modules.affiliates.infrastructure.repository import active_generations
    program = SimpleNamespace(feeds=[
        {"feed_id": "1", "generation": 1, "selected": False},
        {"feed_id": "2", "generation": 2, "selected": True, "available": False},
        {"feed_id": "3", "generation": 3, "selected": True, "available": True},
    ])
    assert active_generations(program) == [("3", 3)]


@pytest.mark.parametrize("url", ["javascript://tidd.ly/x", "https://user:pass@tidd.ly/x", "https://tidd.ly:444/x"])
def test_tracking_url_requires_safe_https(url):
    from app.modules.affiliates.domain.offers import is_network_tracking_url
    assert not is_network_tracking_url(url)


def test_nonfinite_prices_are_missing():
    from app.modules.affiliates.domain.offers import parse_money
    assert parse_money(float("nan")) is None


def test_td_tracking_host_must_be_exact():
    from types import SimpleNamespace
    from app.modules.affiliates.application.import_offer import ImportOfferUseCase
    program = SimpleNamespace(supports_links=True, deeplink_verified_at=None)
    result = ImportOfferUseCase(None, None, None)._td_link(
        program, {"tracking_url": "https://eviltradedoubler.com/x"}, "https://www.mediamarkt.es/x"
    )
    assert result["status"] == "unavailable"


def test_td_feed_uses_documented_modification_time():
    client = _td(lambda r: httpx.Response(200, json={"feeds": [{"feedId": 1, "lastModifiedTime": "2026-11-08T10:00:00Z"}]}))
    assert client.product_feeds()[0]["last_imported"] == "2026-11-08T10:00:00Z"


def test_feed_unknown_schema_is_error_not_empty_catalog(tmp_path):
    path = tmp_path / "invalid.csv"
    path.write_text("id,title,price\n1,Product,100\n", encoding="utf-8")
    with pytest.raises(NetworkError):
        list(iter_feed_rows(path, 10000, 10))
