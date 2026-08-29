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
    session.rollback = AsyncMock()
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
    session = service.session

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

    session.add.assert_called_once()
    entry = session.add.call_args.args[0]
    assert entry.user_id == "admin-1"
    assert entry.action == "deal.auto_delete_price_check"
    assert entry.target_type == "deal"
    assert entry.target_id == "deal-1"
    assert entry.payload == {"old_price": 100.0, "new_price": 115.0, "reason": "price_increase"}


# --- run_automatic ---

@pytest.mark.asyncio
async def test_run_automatic_ejecuta_preview_y_execute_y_marca_automatic():
    task = _task(last_run_at=None)
    handler = MagicMock()
    candidate = _candidate()
    handler.evaluate = MagicMock(return_value=PreviewResult(total_checked=3, candidates=[candidate]))
    handler.execute = AsyncMock(return_value=[candidate])
    service, repo, deal_repo = _build_service(task, handler)
    session = service.session

    run = await service.run_automatic("task-1")

    assert run.trigger_type == "automatic"
    assert run.status == "completed"
    assert run.triggered_by is None
    assert run.total_checked == 3
    assert run.total_affected == 1
    assert task.last_run_at is not None

    session.add.assert_called_once()
    entry = session.add.call_args.args[0]
    assert entry.user_id is None
    assert entry.action == "deal.auto_delete_price_check"
    assert entry.target_type == "deal"
    assert entry.target_id == "deal-1"
    assert entry.payload == {"old_price": 100.0, "new_price": 115.0, "reason": "price_increase"}


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


@pytest.mark.asyncio
async def test_run_automatic_hace_rollback_de_la_sesion_antes_de_persistir_el_run_fallido():
    """Si la excepción viene de una operación SQLAlchemy, la sesión queda en
    estado rollback-required; sin un rollback previo, `create_run` fallaría
    con PendingRollbackError y se perdería el registro de fallo. Se
    verifica el orden real de las llamadas, no solo que ambas ocurran
    (ver finding 8)."""
    task = _task(last_run_at=None)
    handler = MagicMock()
    handler.evaluate = MagicMock(side_effect=RuntimeError("Amazon caído"))
    service, repo, _ = _build_service(task, handler)
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
async def test_run_automatic_preserva_total_checked_real_si_evaluate_ok_pero_execute_falla():
    """Si `evaluate()` tuvo éxito y solo `execute()` falla a mitad de
    camino, el run fallido debe guardar el total_checked real de evaluate(),
    no un 0 hardcodeado (ver finding 8)."""
    task = _task(last_run_at=None)
    handler = MagicMock()
    candidate = _candidate()
    handler.evaluate = MagicMock(return_value=PreviewResult(total_checked=7, candidates=[candidate]))
    handler.execute = AsyncMock(side_effect=RuntimeError("fallo borrando el deal"))
    service, repo, _ = _build_service(task, handler)

    with pytest.raises(RuntimeError):
        await service.run_automatic("task-1")

    created_run = repo.create_run.await_args.args[0]
    assert created_run.status == "failed"
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
    """`Session.rollback()` expira TODOS los objetos ORM del identity map,
    incluida la PK: si el except leyera `task.id` DESPUÉS del rollback,
    reventaría con MissingGreenlet (el scheduler corre bajo `asyncio.run`
    plano, sin contexto greenlet vivo). Debe usar el `task_id` recibido
    como parámetro del método, sin volver a tocar el ORM tras el rollback."""
    task = _ExpiringTask(
        id="task-1", task_type="price_check", config={"price_tolerance_percent": 10}, last_run_at=None,
    )
    handler = MagicMock()
    handler.evaluate = MagicMock(side_effect=RuntimeError("Amazon caído"))
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=task)
    repo.create_run = AsyncMock(side_effect=lambda run: run)
    deal_repo = MagicMock()
    deal_repo.get_active_without_expiry_with_asin = AsyncMock(return_value=["deal-obj"])
    session = MagicMock()
    session.rollback = AsyncMock(side_effect=task.expire)
    service = ScheduledTaskService(repo, deal_repo, {"price_check": handler}, session)

    with pytest.raises(RuntimeError, match="Amazon caído"):
        await service.run_automatic("task-1")

    created_run = repo.create_run.await_args.args[0]
    assert created_run.task_id == "task-1"


from app.modules.scheduled_tasks.domain.exceptions import (
    ItemAlreadyRestoredError,
    RestoreFailedError,
    RunItemNotFound,
)


def _run_item(**overrides):
    base = dict(
        id="item-1",
        title="Producto X",
        slug="producto-x",
        description="desc",
        short_description="Eslogan corto",
        image_url="https://img/x.jpg",
        affiliate_url="https://amazon.es/dp/B0D9WH9WLD",
        source_url=None,
        external_id="B0D9WH9WLD",
        store_id="store-1",
        category_id="cat-1",
        subcategory_id=None,
        old_price=Decimal("100.00"),
        previous_price=Decimal("150.00"),
        discount_percentage=33,
        restored_at=None,
        restored_deal_id=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _build_service_for_history():
    repo = MagicMock()
    deal_repo = MagicMock()
    session = MagicMock()
    service = ScheduledTaskService(repo, deal_repo, {}, session)
    return service, repo, deal_repo


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


@pytest.mark.asyncio
async def test_restore_item_crea_deal_activo_y_marca_restaurado():
    service, repo, deal_repo = _build_service_for_history()
    item = _run_item()
    repo.get_run_item_by_id = AsyncMock(return_value=item)
    repo.update_run_item = AsyncMock(side_effect=lambda i: i)
    created = SimpleNamespace(id="new-deal-1")
    reloaded = SimpleNamespace(id="new-deal-1", title="Producto X", store=None, category=None)
    deal_repo.create = AsyncMock(return_value=created)
    deal_repo.get_by_id = AsyncMock(return_value=reloaded)

    result = await service.restore_item("item-1")

    assert result is reloaded  # recargado con relaciones precargadas, no el objeto crudo de create()
    deal_repo.get_by_id.assert_awaited_once_with("new-deal-1")
    created_deal = deal_repo.create.call_args.args[0]
    assert created_deal.title == "Producto X"
    assert created_deal.status == "active"
    assert created_deal.current_price == Decimal("100.00")
    assert created_deal.previous_price == Decimal("150.00")
    assert created_deal.discount_percentage == 33
    assert created_deal.short_description == "Eslogan corto"
    assert item.restored_at is not None
    assert item.restored_deal_id == "new-deal-1"
    repo.update_run_item.assert_awaited_once_with(item)


@pytest.mark.asyncio
async def test_restore_item_lanza_not_found_si_no_existe():
    service, repo, _ = _build_service_for_history()
    repo.get_run_item_by_id = AsyncMock(return_value=None)

    with pytest.raises(RunItemNotFound):
        await service.restore_item("no-existe")


@pytest.mark.asyncio
async def test_restore_item_lanza_conflict_si_ya_estaba_restaurado():
    service, repo, _ = _build_service_for_history()
    item = _run_item(restored_at=datetime(2026, 8, 1, tzinfo=timezone.utc), restored_deal_id="old-deal")
    repo.get_run_item_by_id = AsyncMock(return_value=item)

    with pytest.raises(ItemAlreadyRestoredError):
        await service.restore_item("item-1")


@pytest.mark.asyncio
async def test_restore_item_traduce_integrity_error_a_restore_failed():
    from sqlalchemy.exc import IntegrityError

    service, repo, deal_repo = _build_service_for_history()
    item = _run_item()
    repo.get_run_item_by_id = AsyncMock(return_value=item)
    deal_repo.create = AsyncMock(side_effect=IntegrityError("stmt", {}, Exception("fk violation")))

    with pytest.raises(RestoreFailedError):
        await service.restore_item("item-1")
