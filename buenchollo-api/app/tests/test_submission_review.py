"""Tests de moderación admin de propuestas (listar, aprobar, rechazar)."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import AuthenticatedUser, get_current_user, require_admin
from app.main import app
from app.modules.deals.api.router import get_deal_service
from app.modules.deals.domain.exceptions import DuplicateDealError
from app.modules.submissions.api import admin_router
from app.modules.submissions.api.dependencies import (
    get_submission_notifier,
    get_submission_repository,
)
from app.modules.submissions.domain.models import DealSubmission

ASIN = "B0ABCDEFGH"
SUB_ID = "11111111-1111-4111-8111-111111111111"
OTHER_ID = "22222222-2222-4222-8222-222222222222"
ADMIN_ID = "33333333-3333-4333-8333-333333333333"
AUTHOR_ID = "44444444-4444-4444-8444-444444444444"
BASE = "/v1/admin/submissions"
TAG = "buenchollo0b-21"


def make_sub(**over):
    fields = dict(
        id=SUB_ID,
        user_id=AUTHOR_ID,
        title="Auriculares",
        current_price=Decimal("10"),
        original_url="https://www.amazon.es/dp/" + ASIN,
        canonical_url=f"https://www.amazon.es/dp/{ASIN}",
        affiliate_url="a",
        asin=ASIN,
        status="pending",
        images=[],
        warnings=["not_affiliable"],
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    fields.update(over)
    sub = DealSubmission(**fields)
    sub.__dict__["user"] = SimpleNamespace(username="ana", display_name="Ana", avatar_url=None)
    return sub


class FakeRepo:
    def __init__(self, subs=None, live=None, expired=None, log=None):
        self.subs = {s.id: s for s in (subs or [])}
        self.live, self.expired = live, expired or []
        self.log = log if log is not None else []
        self.expired_ids: set[str] = set()

    async def get(self, id):
        return self.subs.get(id)

    async def claim_pending(self, id, new_status):
        sub = self.subs.get(id)
        self.log.append(f"claim:{new_status}")
        return bool(sub and sub.status == "pending")

    async def find_live_deal(self, asin, canonical_url):
        return self.live

    async def find_expired_deals(self, asin, canonical_url):
        return self.expired

    async def list_by_status(self, status, limit, offset):
        return [s for s in self.subs.values() if s.status == status][offset : offset + limit]

    async def expired_submission_ids(self, subs):
        return {s.id for s in subs if s.id in self.expired_ids}

    async def count_by_status(self, status):
        return sum(1 for s in self.subs.values() if s.status == status)


class FakeDealService:
    def __init__(self, log):
        self.log = log
        self.created: list[tuple[dict, str]] = []
        self.deleted: list[str] = []
        self.error: Exception | None = None

    async def create_deal(self, data, user_id):
        if self.error:
            raise self.error
        self.log.append("create_deal")
        self.created.append((dict(data), user_id))
        return SimpleNamespace(
            id="55555555-5555-4555-8555-555555555555",
            title=data["title"],
            slug="auriculares",
            current_price=data["current_price"],
            temperature=0,
            status=data["status"] if "status" in data else "active",
            source=data["source"],
            affiliate_url=data["affiliate_url"],
            public_author=None,
        )

    async def delete_deal(self, deal_id):
        self.log.append("delete_deal")
        self.deleted.append(deal_id)
        return True


class FakeDb:
    def __init__(self, log):
        self.log = log
        self.commits = 0

    async def commit(self):
        self.commits += 1
        self.log.append("commit")


class FakeNotifier:
    def __init__(self, log):
        self.log = log

    async def notify_user_decision(self, submission_id):
        self.log.append(f"notify:{submission_id}")


def deal_body(**over):
    data = {
        "title": "Auriculares",
        "current_price": 10,
        "affiliate_url": f"https://www.amazon.es/dp/{ASIN}?tag=otro-21",
        "category_id": "cat-1",
    }
    data.update(over)
    return data


@pytest.fixture
def env(monkeypatch):
    log: list[str] = []
    repo = FakeRepo([make_sub()], log=log)
    service = FakeDealService(log)
    db = FakeDb(log)
    audits: list[dict] = []

    async def fake_audit(_db, **kwargs):
        log.append(f"audit:{kwargs['action']}")
        audits.append(kwargs)

    monkeypatch.setattr(admin_router, "audit_log", fake_audit)
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id=ADMIN_ID, email="a@b.c")
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace(id=ADMIN_ID)
    app.dependency_overrides[get_submission_repository] = lambda: repo
    app.dependency_overrides[get_deal_service] = lambda: service
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_submission_notifier] = lambda: FakeNotifier(log)
    yield SimpleNamespace(repo=repo, service=service, db=db, log=log, audits=audits)
    app.dependency_overrides.clear()


@pytest.fixture
def client(env):
    return TestClient(app)


def test_approve_creates_community_deal_with_our_tag(client, env):
    resp = client.post(f"{BASE}/{SUB_ID}/approve", json=deal_body())
    assert resp.status_code == 200, resp.text
    payload, user_id = env.service.created[0]
    assert payload["source"] == "community"
    assert user_id == AUTHOR_ID
    assert f"tag={get_settings().amazon_affiliate_tag}" in payload["affiliate_url"]
    assert "otro-21" not in payload["affiliate_url"]
    assert payload["external_id"] == ASIN
    sub = env.repo.subs[SUB_ID]
    assert sub.status == "approved"
    assert sub.deal_id == "55555555-5555-4555-8555-555555555555"
    assert sub.reviewed_by == ADMIN_ID and sub.reviewed_at is not None
    assert resp.json()["slug"] == "auriculares"


def test_approve_commits_before_notifying(client, env):
    assert client.post(f"{BASE}/{SUB_ID}/approve", json=deal_body()).status_code == 200
    assert env.log.index("commit") < env.log.index(f"notify:{SUB_ID}")
    assert env.db.commits == 1


def test_reject_commits_before_notifying(client, env):
    assert client.post(f"{BASE}/{SUB_ID}/reject", json={"reason": "No es un chollo"}).status_code == 200
    assert env.log.index("commit") < env.log.index(f"notify:{SUB_ID}")


def test_approve_replaces_expired_deal(client, env):
    env.repo.expired = [SimpleNamespace(id="old-deal", slug="old", title="Old")]
    resp = client.post(f"{BASE}/{SUB_ID}/approve", json=deal_body())
    assert resp.status_code == 200, resp.text
    assert env.service.deleted == ["old-deal"]
    assert env.log.index("delete_deal") < env.log.index("create_deal")
    delete_audit = next(a for a in env.audits if a["action"] == "deal.delete")
    assert delete_audit["payload"] == {
        "reason": "replaced_by_submission",
        "submission_id": SUB_ID,
    }
    assert len(env.service.created) == 1


def test_approve_with_live_deal_conflicts_and_does_not_commit(client, env):
    env.repo.live = SimpleNamespace(id="live-1", slug="live", title="Vivo")
    resp = client.post(f"{BASE}/{SUB_ID}/approve", json=deal_body())
    assert resp.status_code == 409
    assert resp.json()["existing_deal"]["slug"] == "live"
    assert env.db.commits == 0
    assert env.service.created == []
    assert not any(e.startswith("notify") for e in env.log)


def test_approve_duplicate_from_deal_service_does_not_commit(client, env):
    env.service.error = DuplicateDealError("d1", "slug", "T")
    resp = client.post(f"{BASE}/{SUB_ID}/approve", json=deal_body())
    assert resp.status_code == 409
    assert env.db.commits == 0
    assert not any(e.startswith("notify") for e in env.log)


def test_second_approval_conflicts(client, env):
    assert client.post(f"{BASE}/{SUB_ID}/approve", json=deal_body()).status_code == 200
    assert client.post(f"{BASE}/{SUB_ID}/approve", json=deal_body()).status_code == 409


def test_approve_withdrawn_conflicts(client, env):
    env.repo.subs[SUB_ID].status = "withdrawn"
    assert client.post(f"{BASE}/{SUB_ID}/approve", json=deal_body()).status_code == 409
    assert env.db.commits == 0


def test_approve_lost_claim_race_conflicts(client, env):
    async def lost(id, new_status):
        return False

    env.repo.claim_pending = lost
    assert client.post(f"{BASE}/{SUB_ID}/approve", json=deal_body()).status_code == 409
    assert env.service.created == []


def test_approve_future_scheduled_for_becomes_scheduled(client, env):
    future = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    resp = client.post(f"{BASE}/{SUB_ID}/approve", json=deal_body(scheduled_for=future))
    assert resp.status_code == 200, resp.text
    assert env.service.created[0][0]["status"] == "scheduled"


def test_approve_past_scheduled_for_keeps_admin_status(client, env):
    past = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    resp = client.post(f"{BASE}/{SUB_ID}/approve", json=deal_body(scheduled_for=past))
    assert resp.status_code == 200, resp.text
    assert env.service.created[0][0]["status"] == "active"


def test_approve_unknown_and_malformed_id_404(client, env):
    assert client.post(f"{BASE}/{OTHER_ID}/approve", json=deal_body()).status_code == 404
    assert client.post(f"{BASE}/no-es-uuid/approve", json=deal_body()).status_code == 404
    assert client.post(f"{BASE}/no-es-uuid/reject", json={"reason": "motivo"}).status_code == 404
    assert client.get(f"{BASE}/no-es-uuid").status_code == 404


def test_reject_stores_reason(client, env):
    resp = client.post(f"{BASE}/{SUB_ID}/reject", json={"reason": "  Precio no real  "})
    assert resp.status_code == 200, resp.text
    out = resp.json()
    assert out["status"] == "rejected"
    assert out["rejection_reason"] == "Precio no real"
    assert env.repo.subs[SUB_ID].reviewed_by == ADMIN_ID
    assert "audit:submission.reject" in env.log


@pytest.mark.parametrize("reason", ["", "   ", "ab", "x" * 501])
def test_reject_invalid_reason_422(client, reason):
    assert client.post(f"{BASE}/{SUB_ID}/reject", json={"reason": reason}).status_code == 422


def test_reject_not_pending_conflicts(client, env):
    env.repo.subs[SUB_ID].status = "approved"
    assert client.post(f"{BASE}/{SUB_ID}/reject", json={"reason": "motivo"}).status_code == 409


def test_non_admin_forbidden(env):
    def deny():
        raise HTTPException(status_code=403, detail="No tienes permisos de administrador")

    app.dependency_overrides[require_admin] = deny
    c = TestClient(app)
    assert c.get(BASE).status_code == 403
    assert c.get(f"{BASE}/count").status_code == 403
    assert c.post(f"{BASE}/{SUB_ID}/approve", json=deal_body()).status_code == 403
    assert c.post(f"{BASE}/{SUB_ID}/reject", json={"reason": "motivo"}).status_code == 403


def test_count_route_not_shadowed_by_id(client, env):
    resp = client.get(f"{BASE}/count")
    assert resp.status_code == 200
    assert resp.json() == {"pending": 1}


def test_list_includes_author_and_previously_published(client, env):
    env.repo.expired_ids = {SUB_ID}
    resp = client.get(BASE)
    assert resp.status_code == 200, resp.text
    [item] = resp.json()
    assert item["author"]["display_name"] == "Ana"
    assert item["previously_published"] is True
    assert item["original_url"].endswith(ASIN)
    assert item["warnings"] == ["not_affiliable"]


def test_list_filters_by_status_and_validates_it(client, env):
    assert client.get(f"{BASE}?status=approved").json() == []
    assert client.get(f"{BASE}?status=bogus").status_code == 422


def test_detail(client, env):
    resp = client.get(f"{BASE}/{SUB_ID}")
    assert resp.status_code == 200
    assert resp.json()["id"] == SUB_ID
    assert resp.json()["previously_published"] is False
    assert client.get(f"{BASE}/{OTHER_ID}").status_code == 404


def test_approve_replaces_all_expired_matches(client, env):
    env.repo.expired = [
        SimpleNamespace(id="old-by-asin", slug="a", title="A"),
        SimpleNamespace(id="old-by-url", slug="b", title="B"),
    ]
    resp = client.post(f"{BASE}/{SUB_ID}/approve", json=deal_body())
    assert resp.status_code == 200, resp.text
    assert env.service.deleted == ["old-by-asin", "old-by-url"]
    deletes = [a for a in env.audits if a["action"] == "deal.delete"]
    assert [d["target_id"] for d in deletes] == ["old-by-asin", "old-by-url"]
    assert env.log.index("delete_deal") < env.log.index("create_deal")


class FakeDealsRepo:
    """Solo contiene chollos reales; las propuestas viven en otra tabla."""

    def __init__(self):
        self.deals = [
            SimpleNamespace(
                id="d1", title="Chollo real", slug="chollo-real", image_url=None, images=[],
                current_price=5.0, previous_price=None, discount_percentage=None, temperature=1,
                affiliate_url=None, comment_count=0, published_at=None, created_at=None,
                source="manual", public_author=None, store=None, category=None, subcategory=None,
                status="active", description=None, short_description=None,
            )
        ]

    async def get_latest_active(self, limit):
        return self.deals

    async def search_active(self, search=None, **kwargs):
        return [d for d in self.deals if not search or search.lower() in d.title.lower()]

    async def count_active(self, search=None, **kwargs):
        return len(await self.search_active(search=search))

    async def get_by_slug(self, slug):
        return next((d for d in self.deals if d.slug == slug), None)


def test_pending_submission_does_not_leak_into_public_deals(env):
    title = "Auriculares Secretos Pendientes"
    env.repo.subs[SUB_ID].title = title
    from app.modules.deals.api.router import get_deal_repository

    app.dependency_overrides[get_deal_repository] = lambda: FakeDealsRepo()
    c = TestClient(app)
    assert env.repo.subs[SUB_ID].status == "pending"
    for url in (
        "/v1/deals/latest",
        "/v1/deals/page",
        "/v1/deals/page?search=Secretos",
        f"/v1/deals?q={title}",
        f"/v1/deals?search={title}",
    ):
        resp = c.get(url)
        assert resp.status_code == 200, (url, resp.text)
        assert "Secretos" not in resp.text, url
        assert "chollo-real" in resp.text or "search" in url or "q=" in url
    assert c.get("/v1/deals/page").json()["total"] == 1
    assert c.get("/v1/deals/auriculares-secretos-pendientes").status_code == 404
    assert c.get("/v1/deals/chollo-real").status_code == 200


def test_public_deal_queries_never_touch_submissions():
    src = (Path(__file__).parents[1] / "modules" / "deals").rglob("*.py")
    assert not [p for p in src if "DealSubmission" in p.read_text(encoding="utf-8")]


def test_approve_rejects_generic_shortener_without_claiming(client, env):
    resp = client.post(
        f"{BASE}/{SUB_ID}/approve", json=deal_body(affiliate_url="https://bit.ly/3abc")
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Pega el enlace directo del producto, sin acortadores"
    assert env.service.created == []
    assert not any(entry.startswith("claim") for entry in env.log)
