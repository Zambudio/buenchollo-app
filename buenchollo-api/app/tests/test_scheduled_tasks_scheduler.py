from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import Settings
from app.modules.scheduled_tasks.application.scheduler import _execute_due_tasks, _run


def _task(task_id: str, *, enabled: bool = True, run_hour: int = 0, last_run_at=None, frequency_preset="weekly"):
    return SimpleNamespace(
        id=task_id, enabled=enabled, run_hour=run_hour,
        last_run_at=last_run_at, frequency_preset=frequency_preset,
    )


class FakeRepo:
    def __init__(self, tasks):
        self.tasks = tasks

    async def get_enabled_tasks(self):
        return self.tasks


@pytest.mark.asyncio
async def test_execute_due_tasks_ejecuta_solo_las_debidas():
    due = _task("task-1", run_hour=0)
    not_due = _task("task-2", enabled=False)
    repo = FakeRepo([due, not_due])
    service = MagicMock()
    service.run_automatic = AsyncMock()
    session = MagicMock()
    session.commit = AsyncMock()

    executed = await _execute_due_tasks(
        repo, service, session, datetime(2026, 8, 10, 5, tzinfo=timezone.utc)
    )

    assert executed == 1
    service.run_automatic.assert_awaited_once_with("task-1")
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_due_tasks_continua_si_una_tarea_falla():
    task_a = _task("task-1", run_hour=0)
    task_b = _task("task-2", run_hour=0)
    repo = FakeRepo([task_a, task_b])
    service = MagicMock()
    service.run_automatic = AsyncMock(side_effect=[RuntimeError("boom"), None])
    session = MagicMock()
    session.commit = AsyncMock()

    executed = await _execute_due_tasks(
        repo, service, session, datetime(2026, 8, 10, 5, tzinfo=timezone.utc)
    )

    assert executed == 1  # task-1 falló (no cuenta), task-2 se ejecuta igualmente
    assert service.run_automatic.await_count == 2
    # Se comitea tras cada tarea (una por cada una de las 2), no una sola vez
    # al final (ver finding 8): así el fallo de task-1 no puede tirar el
    # trabajo ya bueno de task-2 en un commit final compartido.
    assert session.commit.await_count == 2


@pytest.mark.asyncio
async def test_run_devuelve_cero_sin_database_url():
    settings = Settings(database_url="")

    executed = await _run(settings)

    assert executed == 0
