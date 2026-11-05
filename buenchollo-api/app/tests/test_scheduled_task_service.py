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
        transition="offer_ended",
    )
    base.update(overrides)
    return Candidate(**base)


def _handler(*, checks=("check",), applied=(), collect_error=None, apply_error=None):
    handler = MagicMock()
    handler.collect = AsyncMock(return_value=list(checks), side_effect=collect_error)
    handler.evaluate = MagicMock(
        return_value=PreviewResult(total_checked=len(checks), candidates=list(applied))
    )
    handler.apply = AsyncMock(return_value=list(applied), side_effect=apply_error)
    return handler


def _build_service(task, handler):
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=task)
    repo.update_task = AsyncMock(side_effect=lambda t: t)
    repo.create_run = AsyncMock(side_effect=lambda run: run)
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()
    service = ScheduledTaskService(repo, {"price_check": handler}, session)
    return service, repo


def _build_service_for_history():
    repo = MagicMock()
    service = ScheduledTaskService(repo, {}, MagicMock())
    return service, repo, None


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


def test_is_task_due_diaria_no_se_desplaza_si_ayer_acabo_tras_la_hora():
    """Ayer terminó a las 04:05; hoy a las 04:00 ya toca (antes esperaba a las
    05:00 y la hora de ejecución se iba retrasando cada día)."""
    task = _task(frequency_preset="daily", run_hour=4, last_run_at=datetime(2026, 8, 9, 4, 5, tzinfo=timezone.utc))
    assert is_task_due(task, datetime(2026, 8, 10, 4, 0, tzinfo=timezone.utc)) is True
    assert is_task_due(task, datetime(2026, 8, 9, 23, 0, tzinfo=timezone.utc)) is False


# --- preview ---

@pytest.mark.asyncio
async def test_preview_recoge_y_evalua_sin_aplicar():
    task = _task()
    handler = _handler(checks=["c1", "c2"])
    service, _ = _build_service(task, handler)

    result = await service.preview("task-1")

    handler.collect.assert_awaited_once()
    args = handler.evaluate.call_args.args
    assert args[0] == ["c1", "c2"] and args[1] == task.config
    handler.apply.assert_not_awaited()
    assert result.total_checked == 2


@pytest.mark.asyncio
async def test_preview_lanza_not_found_si_la_tarea_no_existe():
    service, repo = _build_service(_task(), _handler())
    repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(ScheduledTaskNotFound):
        await service.preview("no-existe")


# --- confirm / run ---

@pytest.mark.asyncio
async def test_confirm_aplica_todo_persiste_el_run_y_actualiza_last_run_at():
    task = _task(last_run_at=None)
    candidate = _candidate()
    handler = _handler(checks=["c1", "c2", "c3"], applied=[candidate])
    service, repo = _build_service(task, handler)
    session = service.session

    run = await service.confirm("task-1", triggered_by="admin-1")

    handler.apply.assert_awaited_once()
    assert handler.apply.await_args.args[0] == ["c1", "c2", "c3"]
    assert run.trigger_type == "manual"
    assert run.status == "completed"
    assert run.total_checked == 3
    assert run.total_affected == 1
    assert run.triggered_by == "admin-1"
    assert run.items[0].deal_id_snapshot == "deal-1"
    assert run.items[0].transition == "offer_ended"
    assert run.items[0].reason == "price_increase"
    assert task.last_run_at is not None
    repo.update_task.assert_awaited_once_with(task)

    entry = session.add.call_args.args[0]
    assert entry.user_id == "admin-1"
    assert entry.action == "deal.offer_transition"
    assert entry.target_type == "deal"
    assert entry.target_id == "deal-1"
    assert entry.payload == {
        "transition": "offer_ended", "reason": "price_increase", "old_price": 100.0, "new_price": 115.0,
    }


@pytest.mark.asyncio
async def test_run_automatic_marca_automatic_y_registra_reactivaciones():
    task = _task(last_run_at=None)
    reactivated = _candidate(transition="reactivated", reason="deal_again", new_price=Decimal("90"))
    service, _ = _build_service(task, _handler(applied=[reactivated]))

    run = await service.run_automatic("task-1")

    assert run.trigger_type == "automatic"
    assert run.triggered_by is None
    assert [(i.transition, i.reason) for i in run.items] == [("reactivated", "deal_again")]


@pytest.mark.asyncio
async def test_run_automatic_persiste_run_fallido_y_relanza_si_el_handler_explota():
    task = _task(last_run_at=None)
    service, repo = _build_service(task, _handler(collect_error=RuntimeError("Amazon caído")))

    with pytest.raises(RuntimeError):
        await service.run_automatic("task-1")

    created_run = repo.create_run.await_args.args[0]
    assert created_run.status == "failed"
    assert created_run.trigger_type == "automatic"
    assert "Amazon caído" in created_run.error_message
    assert task.last_run_at is None


@pytest.mark.asyncio
async def test_run_automatic_hace_rollback_de_la_sesion_antes_de_persistir_el_run_fallido():
    task = _task(last_run_at=None)
    service, repo = _build_service(task, _handler(collect_error=RuntimeError("Amazon caído")))
    session = service.session

    call_order: list[str] = []
    session.rollback = AsyncMock(side_effect=lambda: call_order.append("rollback"))
    original_create_run = repo.create_run

    async def _tracking_create_run(run):
        call_order.append("create_run")
        return await original_create_run(run)

    repo.create_run = AsyncMock(side_effect=_tracking_create_run)

    with pytest.raises(RuntimeError):
        await service.run_automatic("task-1")

    assert call_order == ["rollback", "create_run"]


@pytest.mark.asyncio
async def test_run_preserva_total_checked_si_apply_falla():
    task = _task(last_run_at=None)
    handler = _handler(checks=["a"] * 7, apply_error=RuntimeError("fallo escribiendo"))
    service, repo = _build_service(task, handler)

    with pytest.raises(RuntimeError):
        await service.confirm("task-1", triggered_by="admin-1")

    created_run = repo.create_run.await_args.args[0]
    assert created_run.status == "failed"
    assert created_run.trigger_type == "manual"
    assert created_run.total_checked == 7


class _ExpiringTask:
    """Simula que `Session.rollback()` expira los atributos del objeto ORM
    (incluida la PK): tras `expire()`, leer cualquier atributo explota, como
    haría un lazy-refresh de SQLAlchemy fuera de contexto greenlet
    (MissingGreenlet) cuando el rollback ocurre fuera de una request viva
    (el scheduler corre bajo `asyncio.run` plano, no dentro de un endpoint).
    `SimpleNamespace` no sirve para esto porque no tiene semántica de
    expiración."""

    def __init__(self, **attrs):
        object.__setattr__(self, "_attrs", attrs)
        object.__setattr__(self, "_expired", False)

    def expire(self):
        object.__setattr__(self, "_expired", True)

    def __getattr__(self, name):
        if object.__getattribute__(self, "_expired"):
            raise RuntimeError(f"MissingGreenlet simulado: acceso a '{name}' tras expirar (rollback)")
        try:
            return object.__getattribute__(self, "_attrs")[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        object.__getattribute__(self, "_attrs")[name] = value


@pytest.mark.asyncio
async def test_run_automatic_no_relee_task_id_del_orm_tras_el_rollback():
    task = _ExpiringTask(
        id="task-1", task_type="price_check", config={"price_tolerance_percent": 10}, last_run_at=None,
    )
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=task)
    repo.create_run = AsyncMock(side_effect=lambda run: run)
    session = MagicMock()
    session.rollback = AsyncMock(side_effect=task.expire)
    handler = _handler(collect_error=RuntimeError("Amazon caído"))
    service = ScheduledTaskService(repo, {"price_check": handler}, session)

    with pytest.raises(RuntimeError, match="Amazon caído"):
        await service.run_automatic("task-1")

    created_run = repo.create_run.await_args.args[0]
    assert created_run.task_id == "task-1"


@pytest.mark.asyncio
async def test_list_runs_delega_en_el_repositorio():
    service, repo, _ = _build_service_for_history()
    repo.list_runs = AsyncMock(return_value=["run-a"])

    result = await service.list_runs("task-1", limit=10, offset=0)

    repo.list_runs.assert_awaited_once_with("task-1", limit=10, offset=0)
    assert result == ["run-a"]


@pytest.mark.asyncio
async def test_delete_run_true_si_existia():
    service, repo, _ = _build_service_for_history()
    run = SimpleNamespace(id="run-1")
    repo.get_run_by_id = AsyncMock(return_value=run)
    repo.delete_run = AsyncMock()

    deleted = await service.delete_run("run-1")

    assert deleted is True
    repo.delete_run.assert_awaited_once_with(run)


@pytest.mark.asyncio
async def test_delete_run_false_si_no_existia():
    service, repo, _ = _build_service_for_history()
    repo.get_run_by_id = AsyncMock(return_value=None)

    deleted = await service.delete_run("no-existe")

    assert deleted is False


@pytest.mark.asyncio
async def test_bulk_delete_runs_delega_en_el_repositorio():
    service, repo, _ = _build_service_for_history()
    repo.delete_runs_by_ids = AsyncMock(return_value=3)

    count = await service.bulk_delete_runs(["r1", "r2", "r3"])

    assert count == 3
    repo.delete_runs_by_ids.assert_awaited_once_with(["r1", "r2", "r3"])
