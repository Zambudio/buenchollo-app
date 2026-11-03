"""SubmissionRepository contra PostgreSQL real, siempre dentro de una transacción
que se revierte (nunca se hace commit).

Requiere DATABASE_URL (buenchollo-api/.env). Se excluye del CI con -m "not integration".
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import get_settings
from app.modules.deals.domain.models import Deal
from app.modules.submissions.domain.models import PENDING, WITHDRAWN, DealSubmission
from app.modules.submissions.infrastructure.repository import SubmissionRepository

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest_asyncio.fixture
async def session():
    url = get_settings().database_url
    if not url:
        pytest.fail("DATABASE_URL no configurada: no se puede ejecutar el test de integración")
    engine = create_async_engine(url, connect_args={"statement_cache_size": 0})
    conn = await engine.connect()
    trans = await conn.begin()
    try:
        yield AsyncSession(bind=conn, expire_on_commit=False)
    finally:
        await trans.rollback()
        await conn.close()
        await engine.dispose()


def _tag() -> str:
    return uuid.uuid4().hex[:12]


async def _existing_ids(session: AsyncSession) -> tuple[str, str]:
    user_id = (await session.execute(text("SELECT user_id FROM profiles LIMIT 1"))).scalar_one()
    category_id = (await session.execute(text("SELECT id FROM categories LIMIT 1"))).scalar_one()
    return str(user_id), str(category_id)


def _submission(user_id: str, category_id: str, tag: str, **over) -> DealSubmission:
    fields = dict(
        user_id=user_id,
        status=PENDING,
        original_url=f"https://www.amazon.es/dp/{tag}",
        canonical_url=f"https://www.amazon.es/dp/{tag}",
        affiliate_url=f"https://www.amazon.es/dp/{tag}?tag=x-21",
        asin=tag[:10].upper(),
        title="Test integración",
        current_price=Decimal("10.00"),
        category_id=category_id,
        images=[],
        warnings=[],
    )
    fields.update(over)
    return DealSubmission(**fields)


def _deal(tag: str, status: str, category_id: str, asin: str | None, canonical: str) -> Deal:
    return Deal(
        title=f"Deal {tag}",
        slug=f"it-{tag}-{status}",
        current_price=Decimal("5.00"),
        affiliate_url="https://example.com/a",
        status=status,
        category_id=category_id,
        external_id=asin,
        canonical_url=canonical,
    )


async def test_deal_lookups(session):
    _, category_id = await _existing_ids(session)
    repo = SubmissionRepository(session)
    tag = _tag()
    asin = tag[:10].upper()
    canonical = f"https://www.amazon.es/dp/{asin}"

    assert await repo.find_live_deal(asin, canonical) is None
    assert await repo.find_expired_deal(asin, canonical) is None

    session.add(_deal(tag, "expired", category_id, asin, canonical))
    await session.flush()
    assert await repo.find_live_deal(asin, canonical) is None
    assert (await repo.find_expired_deal(asin, canonical)).status == "expired"

    live_tag = _tag()
    live_asin = live_tag[:10].upper()
    live_canonical = f"https://www.amazon.es/dp/{live_asin}"
    session.add(_deal(live_tag, "active", category_id, live_asin, live_canonical))
    await session.flush()
    assert (await repo.find_live_deal(live_asin, live_canonical)).status == "active"
    assert (await repo.find_live_deal(None, live_canonical)).status == "active"
    assert (await repo.find_live_deal(live_asin, "https://otra.url/x")).status == "active"
    assert await repo.find_expired_deal(live_asin, live_canonical) is None


async def test_pending_counts_unique_and_listing(session):
    user_id, category_id = await _existing_ids(session)
    repo = SubmissionRepository(session)
    tag = _tag()
    before_pending = await repo.count_pending_by_user(user_id)
    before_day = await repo.count_since(user_id, datetime.now(timezone.utc) - timedelta(hours=24))

    sub = await repo.add(_submission(user_id, category_id, tag))
    assert sub.status == PENDING
    assert (await repo.find_pending(sub.asin, sub.canonical_url)).id == sub.id
    assert (await repo.find_pending(None, sub.canonical_url)).id == sub.id
    assert await repo.count_pending_by_user(user_id) == before_pending + 1
    assert (
        await repo.count_since(user_id, datetime.now(timezone.utc) - timedelta(hours=24))
        == before_day + 1
    )
    assert await repo.count_since(user_id, datetime.now(timezone.utc) + timedelta(hours=1)) == 0

    listed = await repo.list_by_user(user_id, 100, 0)
    mine = next(s for s in listed if s.id == sub.id)
    assert mine.category.id == category_id
    assert mine.store is None and mine.subcategory is None and mine.deal is None

    other_url = f"https://www.amazon.es/dp/{_tag()}"
    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            await repo.add(
                _submission(
                    user_id, category_id, _tag(), asin=sub.asin, canonical_url=other_url,
                    original_url=other_url, affiliate_url=other_url,
                )
            )

    assert await repo.claim_pending(sub.id, WITHDRAWN) is True
    assert await repo.claim_pending(sub.id, WITHDRAWN) is False
    assert await repo.find_pending(sub.asin, sub.canonical_url) is None
    assert await repo.count_pending_by_user(user_id) == before_pending
