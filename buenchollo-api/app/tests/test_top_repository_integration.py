import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import get_settings
from app.modules.catalog.domain.models import Product
from app.modules.catalog.infrastructure.top_repository import TopRepository
from app.modules.categories.domain.models import Category
from app.modules.deals.domain.models import Deal

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine(get_settings().database_url, connect_args={"statement_cache_size": 0})
    conn = await engine.connect()
    trans = await conn.begin()
    try:
        yield AsyncSession(bind=conn, expire_on_commit=False)
    finally:
        await trans.rollback()
        await conn.close()
        await engine.dispose()


async def test_todos_los_productos_compiten_y_el_voto_reordena(session):
    suffix = uuid.uuid4().hex[:8]
    parent = Category(name="Informática", slug=f"informatica-top-{suffix}", is_active=True)
    session.add(parent)
    await session.flush()
    child = Category(name="Monitores", slug=f"monitores-top-{suffix}", parent_id=parent.id, is_active=True)
    session.add(child)
    await session.flush()
    first = Product(slug=f"monitor-a-{suffix}", title="Monitor A", category_id=parent.id, subcategory_id=child.id)
    second = Product(slug=f"monitor-b-{suffix}", title="Monitor B", category_id=parent.id, subcategory_id=child.id)
    draft_only = Product(slug=f"monitor-draft-{suffix}", title="Monitor sin publicar", category_id=parent.id, subcategory_id=child.id)
    session.add_all([first, second, draft_only])
    await session.flush()
    session.add_all([
        Deal(title="Monitor A", slug=f"chollo-a-{suffix}", current_price=100, affiliate_url="https://example.com/a", product_id=first.id, status="expired"),
        Deal(title="Monitor B", slug=f"chollo-b-{suffix}", current_price=80, affiliate_url="https://example.com/b", product_id=second.id, status="active"),
        Deal(title="Monitor sin publicar", slug=f"chollo-draft-{suffix}", current_price=70, affiliate_url="https://example.com/draft", product_id=draft_only.id, status="draft"),
    ])
    await session.flush()

    repo = TopRepository(session)
    before = await repo.ranked_products(child)
    assert {item["id"] for item in before} == {first.id, second.id}
    assert all(item["vote_count"] == 0 for item in before)
    assert before[0]["id"] == second.id
    assert await repo.product_exists(second.id)
    assert not await repo.product_exists(draft_only.id)

    user_id = str(uuid.uuid4())
    assert await repo.toggle_vote(second.id, user_id) is True
    ranked = await repo.ranked_products(child)
    assert ranked[0]["id"] == second.id
    assert ranked[0]["vote_count"] == 1
    assert ranked[0]["current_price"] == 80
    assert (await repo.my_votes([first.id, second.id], user_id)) == [second.id]
    assert await repo.toggle_vote(second.id, user_id) is False
    assert all(item["vote_count"] == 0 for item in await repo.ranked_products(child))
