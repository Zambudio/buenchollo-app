from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.dialects import postgresql

from app.modules.scheduled_tasks.infrastructure.repository import ScheduledTaskRepository


def _repo_with_mocked_session():
    result = Mock()
    result.scalars.return_value.all.return_value = []
    result.scalars.return_value.first.return_value = None
    session = Mock()
    session.execute = AsyncMock(return_value=result)
    return ScheduledTaskRepository(session), session


def _compiled_sql(session) -> str:
    statement = session.execute.await_args.args[0]
    return str(
        statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )


@pytest.mark.asyncio
async def test_get_enabled_tasks_filters_by_enabled():
    repo, session = _repo_with_mocked_session()

    await repo.get_enabled_tasks()

    sql = _compiled_sql(session)
    assert "scheduled_tasks.enabled = true" in sql


@pytest.mark.asyncio
async def test_get_by_id_filters_by_id():
    repo, session = _repo_with_mocked_session()

    await repo.get_by_id("task-1")

    sql = _compiled_sql(session)
    # PostgreSQL UUID type normalizes "task-1" to 'task1' with literal_binds
    assert "scheduled_tasks.id = 'task1'" in sql


@pytest.mark.asyncio
async def test_list_runs_filters_by_task_and_orders_recent_first():
    repo, session = _repo_with_mocked_session()

    await repo.list_runs("task-1", limit=50, offset=0)

    sql = _compiled_sql(session)
    # PostgreSQL UUID type normalizes "task-1" to 'task1' with literal_binds
    assert "scheduled_task_runs.task_id = 'task1'" in sql
    assert "ORDER BY scheduled_task_runs.started_at DESC" in sql
    assert "LIMIT 50" in sql
