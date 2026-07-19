from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.dialects import postgresql

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
