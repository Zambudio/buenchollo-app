from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from app.core.config import Settings
from app.modules.scheduled_tasks.application.scheduler import _build_service, _execute_due_tasks, _run
from app.modules.scheduled_tasks.application.scheduled_task_service import ScheduledTaskService


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


class _ExpiringTask:
    """Simula que `Session.rollback()` (disparado dentro de `run_automatic`
    al fallar una tarea) expira TODOS los objetos ORM del identity map, no
    solo el de la tarea que falló: tras `expire()`, leer cualquier atributo
    explota, como un lazy-refresh de SQLAlchemy fuera de contexto greenlet
    (MissingGreenlet). `SimpleNamespace` no sirve para esto: no tiene
    semántica de expiración."""

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
async def test_execute_due_tasks_no_relee_atributos_orm_de_una_tarea_hermana_tras_rollback():
    """Si `run_automatic` de la tarea A falla y hace rollback de la sesión,
    eso expira TODOS los objetos ORM ya cargados, incluida la tarea B que
    todavía no se ha procesado. Los ids de las tareas debidas deben
    calcularse una sola vez, ANTES del bucle que llama a `run_automatic`,
    para no releer atributos (`enabled`, `run_hour`, ...) de una tarea
    hermana ya expirada en la siguiente iteración — si no, revienta con
    MissingGreenlet fuera del try/except de aislamiento por tarea, y aborta
    el tick entero del scheduler en vez de solo la tarea que falló."""
    task_a = _ExpiringTask(id="task-1", enabled=True, run_hour=0, last_run_at=None, frequency_preset="weekly")
    task_b = _ExpiringTask(id="task-2", enabled=True, run_hour=0, last_run_at=None, frequency_preset="weekly")
    repo = FakeRepo([task_a, task_b])
    session = MagicMock()
    session.commit = AsyncMock()
    service = MagicMock()

    async def _run_automatic_simula_rollback_que_expira_todo(task_id):
        # Efecto real de `Session.rollback()` dentro de `run_automatic`:
        # expira TODOS los objetos ORM del identity map, no solo el de la
        # tarea que se estaba procesando.
        task_a.expire()
        task_b.expire()

    service.run_automatic = AsyncMock(side_effect=_run_automatic_simula_rollback_que_expira_todo)

    executed = await _execute_due_tasks(
        repo, service, session, datetime(2026, 8, 10, 5, tzinfo=timezone.utc)
    )

    assert executed == 2
    assert service.run_automatic.await_args_list == [call("task-1"), call("task-2")]


@pytest.mark.asyncio
async def test_run_devuelve_cero_sin_database_url():
    settings = Settings(database_url="")

    executed = await _run(settings)

    assert executed == 0


def test_build_service_cablea_dependencias_sin_nameerror():
    """Regresión: `_run` instanciaba `DealRepository` sin importarlo (el import
    se perdió al extraer `build_task_handlers` a factory.py), así que cada tick
    automático del scheduler reventaba con NameError, lo capturaba el `except
    Exception` de `_run` ("Fallo global del worker de tareas programadas") y la
    tarea no se ejecutaba nunca sola — solo funcionaba el botón "Ejecutar ahora"
    (otra ruta, el router de FastAPI). Ningún test llegaba a esa línea: el de
    `_run` retorna antes por falta de DATABASE_URL y los de `_execute_due_tasks`
    inyectan un `service` ya mockeado."""
    session = MagicMock()
    settings = Settings(database_url="postgresql+asyncpg://user:pass@localhost/db")

    repo, service = _build_service(session, settings)

    assert isinstance(service, ScheduledTaskService)
    assert service.deal_repo is not None
    assert "price_check" in service.handlers
