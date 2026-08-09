from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.scheduled_tasks.application.scheduled_task_service import (
    FREQUENCY_DAYS,
    ScheduledTaskService,
    is_task_due,
)
from app.modules.scheduled_tasks.application.task_handler import Candidate, PreviewResult
from app.modules.scheduled_tasks.domain.exceptions import ScheduledTaskNotFound


def _task(**overrides):
    base = dict(
        id="task-1",
        task_type="price_check",
        enabled=True,
        frequency_preset="weekly",
        run_hour=4,
        config={"price_tolerance_percent": 10},
        last_run_at=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _candidate(**overrides):
    base = dict(
        deal_id="deal-1", title="X", slug="x", image_url=None, description=None,
        store_id=None, store_name=None, category_id=None, subcategory_id=None,
        external_id="B0D9WH9WLD", affiliate_url="https://a", source_url=None,
        old_price=Decimal("100.00"), new_price=Decimal("115.00"), reason="price_increase",
    )
    base.update(overrides)
    return Candidate(**base)


def _build_service(task, handler):
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=task)
    repo.update_task = AsyncMock(side_effect=lambda t: t)
    repo.create_run = AsyncMock(side_effect=lambda run: run)
    deal_repo = MagicMock()
    deal_repo.get_active_without_expiry_with_asin = AsyncMock(return_value=["deal-obj"])
    session = MagicMock()
    session.begin_nested = MagicMock(return_value=_NoopAsyncCtx())
    session.add = MagicMock()
    session.flush = AsyncMock()
    service = ScheduledTaskService(repo, deal_repo, {"price_check": handler}, session)
    return service, repo, deal_repo


class _NoopAsyncCtx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


# --- is_task_due ---

def test_is_task_due_false_si_deshabilitada():
    task = _task(enabled=False)
    assert is_task_due(task, datetime(2026, 8, 10, 5, tzinfo=timezone.utc)) is False


def test_is_task_due_false_antes_de_run_hour():
    task = _task(run_hour=4)
    assert is_task_due(task, datetime(2026, 8, 10, 3, 0, tzinfo=timezone.utc)) is False


def test_is_task_due_true_primera_vez_tras_run_hour():
    task = _task(run_hour=4, last_run_at=None)
    assert is_task_due(task, datetime(2026, 8, 10, 5, 0, tzinfo=timezone.utc)) is True


def test_is_task_due_false_si_no_han_pasado_los_dias_de_frecuencia():
    last_run = datetime(2026, 8, 5, 5, 0, tzinfo=timezone.utc)
    task = _task(frequency_preset="weekly", run_hour=4, last_run_at=last_run)
    now = last_run + timedelta(days=3)
    assert is_task_due(task, now) is False


def test_is_task_due_true_si_ya_paso_el_intervalo_de_frecuencia():
    last_run = datetime(2026, 8, 1, 5, 0, tzinfo=timezone.utc)
    task = _task(frequency_preset="weekly", run_hour=4, last_run_at=last_run)
    now = last_run + timedelta(days=FREQUENCY_DAYS["weekly"])
    assert is_task_due(task, now) is True


# --- preview ---

@pytest.mark.asyncio
async def test_preview_delega_en_el_handler_con_los_deals_y_config_de_la_tarea():
    task = _task()
    handler = MagicMock()
    handler.evaluate = MagicMock(return_value=PreviewResult(total_checked=1, candidates=[]))
    service, repo, deal_repo = _build_service(task, handler)

    result = await service.preview("task-1")

    deal_repo.get_active_without_expiry_with_asin.assert_awaited_once()
    handler.evaluate.assert_called_once_with(["deal-obj"], task.config)
    assert result.total_checked == 1


@pytest.mark.asyncio
async def test_preview_lanza_not_found_si_la_tarea_no_existe():
    handler = MagicMock()
    service, repo, _ = _build_service(_task(), handler)
    repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(ScheduledTaskNotFound):
        await service.preview("no-existe")


# --- confirm ---

@pytest.mark.asyncio
async def test_confirm_borra_persiste_el_run_y_actualiza_last_run_at():
    task = _task(last_run_at=None)
    handler = MagicMock()
    candidate = _candidate()
    handler.execute = AsyncMock(return_value=[candidate])
    service, repo, _ = _build_service(task, handler)

    run = await service.confirm("task-1", total_checked=5, candidates=[candidate], triggered_by="admin-1")

    handler.execute.assert_awaited_once_with([candidate])
    assert run.trigger_type == "manual"
    assert run.status == "completed"
    assert run.total_checked == 5
    assert run.total_affected == 1
    assert run.triggered_by == "admin-1"
    assert len(run.items) == 1
    assert run.items[0].deal_id_snapshot == "deal-1"
    assert run.items[0].reason == "price_increase"
    assert task.last_run_at is not None
    repo.update_task.assert_awaited_once_with(task)


# --- run_automatic ---

@pytest.mark.asyncio
async def test_run_automatic_ejecuta_preview_y_execute_y_marca_automatic():
    task = _task(last_run_at=None)
    handler = MagicMock()
    candidate = _candidate()
    handler.evaluate = MagicMock(return_value=PreviewResult(total_checked=3, candidates=[candidate]))
    handler.execute = AsyncMock(return_value=[candidate])
    service, repo, deal_repo = _build_service(task, handler)

    run = await service.run_automatic("task-1")

    assert run.trigger_type == "automatic"
    assert run.status == "completed"
    assert run.triggered_by is None
    assert run.total_checked == 3
    assert run.total_affected == 1
    assert task.last_run_at is not None


@pytest.mark.asyncio
async def test_run_automatic_persiste_run_fallido_y_relanza_si_el_handler_explota():
    task = _task(last_run_at=None)
    handler = MagicMock()
    handler.evaluate = MagicMock(side_effect=RuntimeError("Amazon caído"))
    service, repo, _ = _build_service(task, handler)

    with pytest.raises(RuntimeError):
        await service.run_automatic("task-1")

    created_run = repo.create_run.await_args.args[0]
    assert created_run.status == "failed"
    assert "Amazon caído" in created_run.error_message
    assert task.last_run_at is None  # no se actualiza en fallo: reintenta en el próximo tick
