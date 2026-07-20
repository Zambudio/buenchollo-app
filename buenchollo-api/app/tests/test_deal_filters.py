from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.dialects import postgresql

from app.modules.deals.api.router import get_deals_page
from app.modules.deals.infrastructure.repository import DealRepository


@pytest.mark.asyncio
async def test_search_active_applies_subcategory_price_discount_and_sort():
    result = Mock()
    result.scalars.return_value.all.return_value = []
    session = Mock()
    session.execute = AsyncMock(return_value=result)

    repo = DealRepository(session)
    await repo.search_active(
        category_id="11111111-1111-1111-1111-111111111111",
        subcategory_id="22222222-2222-2222-2222-222222222222",
        min_price=10,
        max_price=50,
        min_discount=20,
        sort="price_asc",
    )

    statement = session.execute.await_args.args[0]
    sql = str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert "deals.category_id =" in sql
    assert "deals.subcategory_id =" in sql
    assert "deals.current_price >= 10" in sql
    assert "deals.current_price <= 50" in sql
    assert "deals.discount_percentage >= 20" in sql
    assert "ORDER BY deals.current_price ASC" in sql


@pytest.mark.asyncio
async def test_popular_sort_has_stable_tie_breakers_for_pagination():
    result = Mock()
    result.scalars.return_value.all.return_value = []
    session = Mock()
    session.execute = AsyncMock(return_value=result)

    repo = DealRepository(session)
    await repo.search_active(sort="popular", limit=12, offset=12)

    statement = session.execute.await_args.args[0]
    sql = str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert (
        "ORDER BY deals.temperature DESC, deals.published_at DESC, deals.id DESC"
        in sql
    )
    assert "LIMIT 12 OFFSET 12" in sql


@pytest.mark.asyncio
async def test_count_active_applies_the_same_filters_as_the_results():
    result = Mock()
    result.scalar_one.return_value = 7
    session = Mock()
    session.execute = AsyncMock(return_value=result)

    repo = DealRepository(session)
    total = await repo.count_active(
        category_id="11111111-1111-1111-1111-111111111111",
        search="usb",
        min_price=10,
        min_discount=20,
    )

    statement = session.execute.await_args.args[0]
    sql = str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert total == 7
    assert "deals.category_id =" in sql
    assert "deals.title ILIKE '%%usb%%'" in sql
    assert "deals.current_price >= 10" in sql
    assert "deals.discount_percentage >= 20" in sql


@pytest.mark.asyncio
async def test_deals_page_returns_total_and_clamps_an_out_of_range_page():
    repo = Mock(spec=DealRepository)
    repo.count_active = AsyncMock(return_value=25)
    repo.search_active = AsyncMock(return_value=[])

    response = await get_deals_page(
        sort="popular",
        page=99,
        page_size=12,
        category_id=None,
        subcategory_id=None,
        store_id=None,
        search=None,
        min_price=None,
        max_price=None,
        min_discount=None,
        repo=repo,
    )

    assert response.page == 3
    assert response.total == 25
    assert response.total_pages == 3
    repo.search_active.assert_awaited_once_with(
        category_id=None,
        subcategory_id=None,
        store_id=None,
        search=None,
        min_price=None,
        max_price=None,
        min_discount=None,
        sort="popular",
        limit=12,
        offset=24,
    )
