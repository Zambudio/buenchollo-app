"""API tests for POST /v1/submissions/check-link."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.security import AuthenticatedUser, get_current_user
from app.main import app
from app.modules.products.application.preview_product_from_url import (
    ProductProviderUnavailableError,
)
from app.modules.products.domain.entities import ProductPreview
from app.modules.submissions.api.dependencies import (
    get_profile_repository,
    get_submission_repository,
)
from app.modules.submissions.api.router import get_product_provider, get_check_link_use_case

URL = "/v1/submissions/check-link"
ASIN = "B0ABCDEFGH"


class FakeRepo:
    def __init__(self, live=None, pending=None, expired=None, store=None):
        self.live, self.pending, self.expired, self.store = live, pending, expired, store

    async def find_live_deal(self, asin, canonical_url):
        return self.live

    async def find_pending(self, asin, canonical_url):
        return self.pending

    async def find_expired_deal(self, asin, canonical_url):
        return self.expired

    async def find_store_by_host(self, host):
        return self.store


class FakeProvider:
    def __init__(self, product=None, error=None):
        self.product, self.error = product, error

    def get_product_preview(self, url_or_asin):
        if self.error:
            raise self.error
        return self.product


class FakeProfileRepo:
    def __init__(self, display_name="Pedro"):
        self.display_name = display_name

    async def get_by_user_id(self, user_id):
        if self.display_name is None:
            return None
        return SimpleNamespace(display_name=self.display_name)


def deal(status="active"):
    return SimpleNamespace(
        id="d1", slug="mi-chollo", title="Mi chollo", image_url="https://i/x.jpg",
        current_price=9.5, status=status,
    )


PRODUCT = ProductPreview(
    title="Producto Amazon", brand="Marca", asin=ASIN, image_url="https://i/1.jpg",
    current_price=10.0, original_price=20.0, features=[f"f{i}" for i in range(12)],
    images=["https://i/1.jpg"], expires_at="2026-12-01T10:00:00Z",
)


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id="u1", email="a@b.c")
    app.dependency_overrides[get_profile_repository] = lambda: FakeProfileRepo()
    yield TestClient(app)
    app.dependency_overrides.clear()


def setup(repo=None, provider=None):
    app.dependency_overrides[get_submission_repository] = lambda: repo or FakeRepo()
    app.dependency_overrides[get_product_provider] = lambda: provider or FakeProvider(PRODUCT)


def post(client, url=f"https://www.amazon.es/dp/{ASIN}?tag=otro-21"):
    return client.post(URL, json={"url": url})


def test_published(client):
    setup(FakeRepo(live=deal("active")))
    body = post(client).json()
    assert body["status"] == "published"
    assert body["existing_deal"]["slug"] == "mi-chollo"
    assert body["asin"] == ASIN


def test_upcoming(client):
    setup(FakeRepo(live=deal("scheduled")))
    body = post(client).json()
    assert body["status"] == "upcoming"
    assert body["existing_deal"] is None


def test_in_review(client):
    setup(FakeRepo(pending=SimpleNamespace(id="s1")))
    assert post(client).json()["status"] == "in_review"


def test_expired_previously_published(client):
    setup(FakeRepo(expired=deal("expired")))
    body = post(client).json()
    assert body["status"] == "ok"
    assert body["previously_published"] is True


def test_amazon_prefill(client):
    setup()
    body = post(client).json()
    assert body["status"] == "ok"
    assert body["store_name"] == "Amazon"
    assert body["canonical_url"] == f"https://www.amazon.es/dp/{ASIN}"
    assert "tag=buenchollo0b-21" in body["affiliate_url"]
    prefill = body["prefill"]
    assert prefill["title"] == "Producto Amazon"
    assert prefill["previous_price"] == 20.0
    assert prefill["description"].count("\n") == 9
    assert prefill["description"].startswith("- f0")
    assert prefill["expires_at"].startswith("2026-12-01")


def test_provider_unavailable_gives_no_prefill(client):
    setup(provider=FakeProvider(error=ProductProviderUnavailableError("down")))
    resp = post(client)
    assert resp.status_code == 200
    assert resp.json()["prefill"] is None
    assert resp.json()["status"] == "ok"


def test_store_detected_by_host(client):
    store = SimpleNamespace(id="store-1", name="PcComponentes")
    setup(FakeRepo(store=store))
    body = post(client, "https://www.pccomponentes.com/producto?utm_source=x").json()
    assert body["store_id"] == "store-1"
    assert body["store_name"] == "PcComponentes"
    assert body["is_amazon"] is False
    assert body["prefill"] is None


def test_requires_auth():
    app.dependency_overrides.clear()
    resp = TestClient(app).post(URL, json={"url": "https://example.com/x"})
    assert resp.status_code in (401, 403)


def test_profile_incomplete(client):
    setup()
    app.dependency_overrides[get_profile_repository] = lambda: FakeProfileRepo(display_name="  ")
    resp = post(client)
    assert resp.status_code == 403
    assert resp.json()["code"] == "PROFILE_INCOMPLETE"


def test_invalid_text(client):
    setup()
    assert post(client, "hola que tal").status_code == 400


def test_messy_amazon_input_never_500(client):
    setup()
    resp = post(client, "   www.amazon.es/gp/aw/d/B0ABCDEFGH  ")
    assert resp.status_code == 200
    assert resp.json()["asin"] == ASIN


def test_short_link_unresolved_is_400(client):
    from app.modules.submissions.application.check_link import CheckLinkUseCase

    app.dependency_overrides[get_check_link_use_case] = lambda: CheckLinkUseCase(
        FakeRepo(), FakeProvider(PRODUCT), asin_resolver=lambda url: None
    )
    resp = post(client, "https://amzn.to/abc123")
    assert resp.status_code == 400
    assert "enlace de Amazon" in resp.json()["detail"]


def test_short_link_resolved(client):
    from app.modules.submissions.application.check_link import CheckLinkUseCase

    app.dependency_overrides[get_check_link_use_case] = lambda: CheckLinkUseCase(
        FakeRepo(live=deal()), FakeProvider(PRODUCT), asin_resolver=lambda url: ASIN
    )
    body = post(client, "https://amzn.to/abc123").json()
    assert body["asin"] == ASIN
    assert body["status"] == "published"


@pytest.mark.parametrize(
    "url",
    ["https://bit.ly/3abcd", "https://tinyurl.com/xyz", "https://t.co/abc", "https://s.click.aliexpress.com/e/_abc"],
)
def test_generic_shortener_is_400(client, url):
    setup()
    resp = post(client, url)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Pega el enlace directo del producto, sin acortadores"
