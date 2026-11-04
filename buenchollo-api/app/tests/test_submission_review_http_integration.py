"""Aprobar/rechazar propuestas por HTTP contra PostgreSQL real (I4).

A diferencia de test_submission_repository_integration.py, aquí se usa el
`get_db` REAL: el endpoint hace COMMIT, así que estos tests solo se ejecutan
contra una BD desechable (el Postgres vanilla del CI). Contra Supabase (BD
compartida dev/prod) se saltan.
"""

import asyncio
import uuid
from decimal import Decimal
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.audit.models import AuditLog
from app.core.config import get_settings
from app.core.security import AuthenticatedUser, get_current_user, require_admin
from app.modules.categories.domain.models import Category
from app.modules.deals.domain.models import Deal
from app.modules.submissions.api.dependencies import get_submission_notifier
from app.modules.submissions.domain.models import PENDING, DealSubmission
from app.modules.users.domain.models import Profile

_DB_URL = get_settings().database_url or ""

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        "supabase" in (urlsplit(_DB_URL).hostname or ""),
        reason=(
            "El endpoint hace COMMIT: solo contra una BD desechable (CI), "
            "nunca contra Supabase (BD compartida dev/prod)"
        ),
    ),
    pytest.mark.skipif(not _DB_URL, reason="DATABASE_URL no configurada"),
]


class _Notifier:
    def __init__(self):
        self.calls: list[str] = []

    async def notify_user_decision(self, submission_id):
        self.calls.append(submission_id)


def _run(coro_fn):
    async def wrapper():
        engine = create_async_engine(
            _DB_URL, poolclass=NullPool, connect_args={"statement_cache_size": 0}
        )
        try:
            async with AsyncSession(engine, expire_on_commit=False) as session:
                return await coro_fn(session)
        finally:
            await engine.dispose()

    return asyncio.run(wrapper())


@pytest.fixture
def seeded():
    tag = uuid.uuid4().hex[:10]
    asin = ("B0" + tag[:8]).upper()
    ids = SimpleNamespace(
        tag=tag,
        asin=asin,
        author=str(uuid.uuid4()),
        admin=str(uuid.uuid4()),
        category=None,
        subcategory=None,
        expired=None,
        submission=None,
    )

    async def seed(session):
        session.add_all(
            [
                Profile(user_id=ids.author, username=f"autor-{tag}", display_name="Autora"),
                Profile(user_id=ids.admin, username=f"admin-{tag}", display_name="Admin"),
            ]
        )
        category = Category(name=f"Cat {tag}", slug=f"cat-{tag}")
        session.add(category)
        await session.flush()
        subcategory = Category(name=f"Sub {tag}", slug=f"sub-{tag}", parent_id=category.id)
        session.add(subcategory)
        canonical = f"https://www.amazon.es/dp/{asin}"
        expired = Deal(
            title=f"Viejo {tag}",
            slug=f"viejo-{tag}",
            current_price=Decimal("20.00"),
            affiliate_url=canonical,
            status="expired",
            category_id=category.id,
            external_id=asin,
            canonical_url=canonical,
        )
        session.add(expired)
        await session.flush()
        submission = DealSubmission(
            user_id=ids.author,
            status=PENDING,
            original_url=f"{canonical}?tag=otro-21",
            canonical_url=canonical,
            affiliate_url=f"{canonical}?tag=x-21",
            asin=asin,
            title=f"Propuesta {tag}",
            current_price=Decimal("10.00"),
            category_id=category.id,
            subcategory_id=subcategory.id,
            images=[],
            warnings=[],
        )
        session.add(submission)
        await session.commit()
        ids.category, ids.subcategory = category.id, subcategory.id
        ids.expired, ids.submission = expired.id, submission.id

    _run(seed)
    yield ids

    async def cleanup(session):
        await session.execute(delete(DealSubmission).where(DealSubmission.user_id == ids.author))
        await session.execute(delete(Deal).where(Deal.external_id == ids.asin))
        await session.execute(delete(AuditLog).where(AuditLog.user_id == ids.admin))
        await session.execute(delete(Category).where(Category.id == ids.subcategory))
        await session.execute(delete(Category).where(Category.id == ids.category))
        await session.execute(delete(Profile).where(Profile.user_id.in_([ids.author, ids.admin])))
        await session.commit()

    _run(cleanup)


@pytest.fixture
def api(integration_client, seeded):
    from app.main import app

    notifier = _Notifier()
    admin = AuthenticatedUser(id=seeded.admin, email="admin@x.test")
    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[require_admin] = lambda: admin
    app.dependency_overrides[get_submission_notifier] = lambda: notifier
    yield SimpleNamespace(client=integration_client, notifier=notifier)
    app.dependency_overrides.clear()


def test_approve_creates_community_deal_and_replaces_expired(api, seeded):
    resp = api.client.post(
        f"/v1/admin/submissions/{seeded.submission}/approve",
        json={
            "title": f"Aprobado {seeded.tag}",
            "current_price": 9.99,
            "affiliate_url": f"https://www.amazon.es/dp/{seeded.asin}?tag=otro-21",
            "category_id": seeded.category,
            "subcategory_id": seeded.subcategory,
            "coupon_code": "CUPON10",
            "status": "active",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    tag = get_settings().amazon_affiliate_tag
    assert body["source"] == "community"
    assert body["author"]["username"] == f"autor-{seeded.tag}"
    assert body["coupon_code"] == "CUPON10"
    assert body["external_id"] == seeded.asin
    assert body["affiliate_url"] == f"https://www.amazon.es/dp/{seeded.asin}?tag={tag}"
    assert api.notifier.calls == [seeded.submission]

    async def check(session):
        assert await session.get(Deal, seeded.expired) is None
        sub = await session.get(DealSubmission, seeded.submission)
        assert sub.status == "approved"
        assert sub.deal_id == body["id"]
        assert sub.reviewed_by == seeded.admin
        actions = (
            await session.execute(
                select(AuditLog.action).where(AuditLog.user_id == seeded.admin)
            )
        ).scalars().all()
        assert {"submission.approve", "deal.delete"} <= set(actions)

    _run(check)


def test_reject_persists_reason(api, seeded):
    resp = api.client.post(
        f"/v1/admin/submissions/{seeded.submission}/reject",
        json={"reason": "El precio no es una oferta"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "rejected"
    assert resp.json()["author"]["username"] == f"autor-{seeded.tag}"

    async def check(session):
        sub = await session.get(DealSubmission, seeded.submission)
        assert sub.status == "rejected"
        assert sub.rejection_reason == "El precio no es una oferta"
        assert await session.get(Deal, seeded.expired) is not None

    _run(check)
