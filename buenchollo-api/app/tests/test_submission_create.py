"""API tests for create / list / withdraw of user submissions."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.core.security import AuthenticatedUser, get_current_user
from app.core.rate_limit import limiter
from app.main import app
from app.modules.submissions.api import schemas
from app.modules.submissions.api.dependencies import (
    get_profile_repository,
    get_submission_repository,
)
from app.modules.submissions.api.router import get_category_repository
from app.modules.submissions.domain.models import DealSubmission

ASIN = "B0ABCDEFGH"
URL = "/v1/submissions"
BUCKET = "https://proj.supabase.co/storage/v1/object/public/deal-images/submissions/"
AMAZON_IMG = "https://m.media-amazon.com/images/I/a.jpg"


class FakeRepo:
    def __init__(self, live=None, pending=None, pending_count=0, day_count=0, add_error=None):
        self.live, self.pending = live, pending
        self.pending_count, self.day_count, self.add_error = pending_count, day_count, add_error
        self.rows: list[DealSubmission] = []

    async def find_live_deal(self, asin, canonical_url):
        return self.live

    async def find_pending(self, asin, canonical_url):
        return self.pending

    async def find_expired_deal(self, asin, canonical_url):
        return None

    async def find_store_by_host(self, host):
        return None

    async def count_pending_by_user(self, user_id):
        return self.pending_count

    async def count_since(self, user_id, since):
        return self.day_count

    async def add(self, sub):
        if self.add_error:
            raise self.add_error
        sub.id = "sub-1"
        sub.created_at = datetime.now(timezone.utc)
        self.rows.append(sub)
        return sub

    async def list_by_user(self, user_id, limit, offset):
        return [r for r in self.rows if r.user_id == user_id][offset : offset + limit]

    async def get(self, id):
        return next((r for r in self.rows if r.id == id), None)

    async def claim_pending(self, id, new_status):
        row = await self.get(id)
        if row and row.status == "pending":
            row.status = new_status
            return True
        return False


class FakeCategories:
    def __init__(self, known=("cat-1",)):
        self.known = set(known)

    async def get_by_id(self, category_id):
        return SimpleNamespace(id=category_id) if category_id in self.known else None


class FakeProfileRepo:
    async def get_by_user_id(self, user_id):
        return SimpleNamespace(display_name="Pedro")


def body(**over):
    data = {
        "url": f"https://www.amazon.es/dp/{ASIN}?tag=otro-21",
        "title": "  Auriculares  ",
        "description": "Muy buenos",
        "current_price": 10,
        "previous_price": 20,
        "category_id": "cat-1",
        "images": [AMAZON_IMG, BUCKET + "u/1.webp"],
        "image_url": AMAZON_IMG,
    }
    data.update(over)
    return data


def make_row(**over):
    fields = dict(
        user_id="u1", title="x", current_price=1, original_url="u", canonical_url="c",
        affiliate_url="a", status="pending", images=[], warnings=[],
    )
    fields.update(over)
    return DealSubmission(**fields)


@pytest.fixture(autouse=True)
def settings(monkeypatch):
    monkeypatch.setattr(
        schemas, "get_settings", lambda: SimpleNamespace(supabase_url="https://proj.supabase.co/")
    )


@pytest.fixture
def repo():
    limiter.reset()
    r = FakeRepo()
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id="u1", email="a@b.c")
    app.dependency_overrides[get_profile_repository] = lambda: FakeProfileRepo()
    app.dependency_overrides[get_submission_repository] = lambda: r
    app.dependency_overrides[get_category_repository] = lambda: FakeCategories()
    yield r
    app.dependency_overrides.clear()


@pytest.fixture
def client(repo):
    return TestClient(app)


def test_create_pending_rewrites_affiliate(client, repo):
    resp = client.post(URL, json=body())
    assert resp.status_code == 201, resp.text
    out = resp.json()
    assert out["status"] == "pending"
    assert "tag=buenchollo0b-21" in out["affiliate_url"]
    assert "otro-21" not in out["affiliate_url"]
    assert out["title"] == "Auriculares"
    assert out["deal_slug"] is None
    saved = repo.rows[0]
    assert saved.asin == ASIN and saved.user_id == "u1"
    assert saved.current_price == Decimal("10")


def test_duplicate_active_deal(client, repo):
    repo.live = SimpleNamespace(
        id="d1", slug="mi-chollo", title="T", image_url=None, current_price=9.5, status="active"
    )
    resp = client.post(URL, json=body())
    assert resp.status_code == 409
    out = resp.json()
    assert out["code"] == "SUBMISSION_DUPLICATE"
    assert out["reason"] == "published"
    assert out["existing_deal"]["slug"] == "mi-chollo"


def test_duplicate_pending(client, repo):
    repo.pending = SimpleNamespace(id="x")
    resp = client.post(URL, json=body())
    assert resp.status_code == 409
    assert resp.json()["reason"] == "in_review"


def test_integrity_error_is_conflict(client, repo):
    repo.add_error = IntegrityError("insert", {}, Exception("uq"))
    resp = client.post(URL, json=body())
    assert resp.status_code == 409
    assert resp.json()["code"] == "SUBMISSION_DUPLICATE"
    assert resp.json()["reason"] == "in_review"


def test_quota_pending(client, repo):
    repo.pending_count = 5
    resp = client.post(URL, json=body())
    assert resp.status_code == 429
    assert "pendientes" in resp.json()["detail"]


def test_quota_daily(client, repo):
    repo.day_count = 15
    resp = client.post(URL, json=body())
    assert resp.status_code == 429
    assert "24 horas" in resp.json()["detail"]


def test_previous_price_not_greater(client):
    assert client.post(URL, json=body(previous_price=10)).status_code == 422


def test_image_domain_not_allowed(client):
    resp = client.post(URL, json=body(images=["https://evil.com/a.jpg"], image_url=None))
    assert resp.status_code == 422


def test_image_lookalike_hosts_rejected(client):
    for bad in (
        "http://m.media-amazon.com/a.jpg",
        "https://m.media-amazon.com.evil.com/a.jpg",
        "https://proj.supabase.co/storage/v1/object/public/deal-images/other/a.jpg",
        "https://proj.supabase.co.evil.com/storage/v1/object/public/deal-images/submissions/a.jpg",
    ):
        assert client.post(URL, json=body(images=[bad], image_url=None)).status_code == 422, bad


def test_image_url_must_be_in_images(client):
    resp = client.post(URL, json=body(image_url=BUCKET + "u/other.webp"))
    assert resp.status_code == 422


def test_nine_images(client):
    imgs = [f"https://m.media-amazon.com/images/I/{i}.jpg" for i in range(9)]
    assert client.post(URL, json=body(images=imgs, image_url=imgs[0])).status_code == 422


def test_expires_must_be_future_and_after_start(client):
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    assert client.post(URL, json=body(expires_at=past)).status_code == 422
    start = datetime.now(timezone.utc) + timedelta(days=3)
    end = start - timedelta(days=1)
    resp = client.post(URL, json=body(starts_at=start.isoformat(), expires_at=end.isoformat()))
    assert resp.status_code == 422


def test_unknown_category_is_400(client, repo):
    resp = client.post(URL, json=body(category_id="nope"))
    assert resp.status_code == 400
    assert not repo.rows


def test_mine_only_own(client, repo):
    client.post(URL, json=body())
    other = make_row(user_id="u2")
    other.id = "sub-2"
    other.created_at = datetime.now(timezone.utc)
    repo.rows.append(other)
    out = client.get(f"{URL}/mine").json()
    assert [s["id"] for s in out] == ["sub-1"]


def test_mine_includes_deal_slug_and_reason(client, repo):
    approved = make_row(status="approved", deal_id="d1")
    approved.id = "s-a"
    approved.deal = SimpleNamespace(slug="el-slug")
    rejected = make_row(status="rejected", rejection_reason="Sin stock", canonical_url="c2")
    rejected.id = "s-r"
    repo.rows += [approved, rejected]
    out = {s["id"]: s for s in client.get(f"{URL}/mine").json()}
    assert out["s-a"]["deal_slug"] == "el-slug"
    assert out["s-r"]["rejection_reason"] == "Sin stock"
    assert out["s-r"]["deal_slug"] is None


def test_withdraw_foreign_is_404(client, repo):
    client.post(URL, json=body())
    repo.rows[0].user_id = "u2"
    assert client.delete(f"{URL}/sub-1").status_code == 404


def test_withdraw_approved_is_409(client, repo):
    client.post(URL, json=body())
    repo.rows[0].status = "approved"
    assert client.delete(f"{URL}/sub-1").status_code == 409


def test_withdraw_own_pending(client, repo):
    client.post(URL, json=body())
    resp = client.delete(f"{URL}/sub-1")
    assert resp.status_code == 204
    assert repo.rows[0].status == "withdrawn"


def test_withdraw_missing_is_404(client):
    assert client.delete(f"{URL}/nope").status_code == 404
