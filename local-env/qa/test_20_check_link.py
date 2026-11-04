"""Paso 1 del flujo: pegar el enlace. Todo lo que un usuario puede pegar mal."""

import pytest

from conftest import assert_no_5xx, db, detail

AMAZON_ASIN = "B09B8X9RGM"
TAG = "buenchollo0b-21"


def check(pool, url):
    return pool.next("check").post("/v1/submissions/check-link", json={"url": url})


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.amazon.es/dp/{AMAZON_ASIN}",
        f"https://www.amazon.es/dp/{AMAZON_ASIN}?tag=otro-afiliado-21&ref=xyz",
        f"https://www.amazon.es/Echo-Dot-modelo-2022/dp/{AMAZON_ASIN}/ref=sr_1_1?keywords=echo",
        f"https://amazon.es/gp/product/{AMAZON_ASIN}",
        f"http://www.amazon.es/dp/{AMAZON_ASIN}",
        f"  https://www.amazon.es/dp/{AMAZON_ASIN}  ",
        f"Mirad este chollo https://www.amazon.es/dp/{AMAZON_ASIN} !!!",
        f"https://www.amazon.es/dp/{AMAZON_ASIN.lower()}",
    ],
)
def test_amazon_variants_are_normalised_with_our_tag(pool, url):
    resp = check(pool, url)
    assert resp.status_code == 200, detail(resp)
    data = resp.json()
    assert data["is_amazon"] is True
    assert data["asin"] == AMAZON_ASIN
    assert data["canonical_url"] == f"https://www.amazon.es/dp/{AMAZON_ASIN}"
    assert f"tag={TAG}" in data["affiliate_url"]
    assert "otro-afiliado" not in data["affiliate_url"]


@pytest.mark.parametrize(
    "url,fragment",
    [
        ("https://bit.ly/3abcdef", "acortador"),
        ("https://tinyurl.com/abc123", "acortador"),
        ("hola que tal", "enlace"),
        ("", None),
        ("javascript:alert(document.cookie)", "enlace"),
        ("data:text/html,<script>alert(1)</script>", "enlace"),
        ("ftp://www.amazon.es/dp/B09B8X9RGM", "enlace"),
        ("https://", "enlace"),
        ("https://www.amazon.es/" + "a" * 2100, None),
    ],
)
def test_invalid_links_get_a_clear_4xx(pool, url, fragment):
    resp = check(pool, url)
    assert_no_5xx(resp)
    assert 400 <= resp.status_code < 500, detail(resp)
    if fragment:
        assert fragment in detail(resp).lower()


def test_non_json_body_is_422(pool):
    resp = pool.next("check").post(
        "/v1/submissions/check-link", content=b"no json", headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 422, resp.text


def test_missing_url_field_is_422(pool):
    resp = pool.next("check").post("/v1/submissions/check-link", json={"link": "https://x.es"})
    assert resp.status_code == 422, resp.text


def test_other_store_is_accepted_without_prefill(pool):
    resp = check(pool, "https://www.pccomponentes.com/portatil-qa-check")
    assert resp.status_code == 200, detail(resp)
    data = resp.json()
    assert data["is_amazon"] is False
    assert data["prefill"] is None
    assert data["status"] == "ok"


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8000/health",
        "https://localhost/producto",
        "https://192.168.1.10/producto",
        "https://10.0.0.5:8443/oferta",
        "https://[::1]/x",
        "https://169.254.169.254/latest/meta-data/",
        "https://intranet/producto",
    ],
)
def test_internal_or_ip_hosts_are_not_accepted_as_stores(pool, url):
    """Un chollo no puede apuntar a una IP, localhost o un host sin dominio."""
    resp = check(pool, url)
    assert_no_5xx(resp)
    assert 400 <= resp.status_code < 500, detail(resp)


def test_already_published_deal_is_detected(pool):
    row = db(
        "SELECT id::text, slug, canonical_url FROM public.deals "
        "WHERE status = 'active' AND canonical_url LIKE 'https://%' "
        "ORDER BY (canonical_url LIKE 'https://www.amazon.es/dp/%') DESC LIMIT 1"
    )
    if not row:
        pytest.skip("No hay chollos activos con canonical_url en la copia local")
    resp = check(pool, row[0]["canonical_url"])
    assert resp.status_code == 200, detail(resp)
    data = resp.json()
    assert data["status"] == "published", data
    assert data["existing_deal"]["slug"] == row[0]["slug"]


def test_scheduled_deal_is_reported_as_upcoming(pool):
    row = db(
        "SELECT canonical_url FROM public.deals WHERE status = 'scheduled' "
        "AND canonical_url IS NOT NULL LIMIT 1"
    )
    if not row:
        pytest.skip("No hay chollos programados con canonical_url en la copia local")
    resp = check(pool, row[0]["canonical_url"])
    assert resp.status_code == 200, detail(resp)
    assert resp.json()["status"] == "upcoming"
