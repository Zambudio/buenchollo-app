"""Job de mantenimiento de la tarea programada de revisión de precios.

Mismo patrón que `scheduled_deals/application/publication_worker.py`:
engine dedicado con NullPool (proceso de fondo, no el pool del web),
envuelto en `asyncio.run()` porque APScheduler (BackgroundScheduler) sólo
llama funciones síncronas. El bucle de "qué tareas tocan" vive en
`_execute_due_tasks`, separado de la creación del engine/sesión, para
poder testearlo con fakes en vez de mockear SQLAlchemy (mismo motivo por
el que `ScheduledPublicationWorker.process_due` es una clase aparte).
"""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.modules.catalog.application.reactivation_notifier import reactivated_deal_ids
from app.modules.scheduled_tasks.application.factory import build_reactivation_notifier, build_task_handlers
from app.modules.scheduled_tasks.application.scheduled_task_service import (
    ScheduledTaskService,
    is_task_due,
)
from app.modules.scheduled_tasks.domain.exceptions import TaskAlreadyRunningError
from app.modules.scheduled_tasks.infrastructure.repository import ScheduledTaskRepository

logger = logging.getLogger(__name__)


async def _execute_due_tasks(repo, service, session, now_local: datetime, notifier=None) -> int:
    """Comitea tras cada tarea (éxito o fallo ya capturado) en vez de una
    única vez al final: si la tarea A deja la sesión en estado
    rollback-required y eso no se recupera limpiamente, un solo commit final
    podría tirar también el trabajo ya bueno de la tarea B (ver finding 8).

    Los ids de las tareas debidas se calculan todos de una vez, antes del
    bucle que llama a `run_automatic`: si una tarea falla con un error
    SQLAlchemy, `run_automatic` hace rollback de la sesión, lo que expira
    TODOS los objetos ORM ya cargados (incluidas las demás tareas de
    `tasks`). Si `is_task_due` se evaluara dentro del bucle, la siguiente
    iteración leería atributos de una tarea ya expirada fuera de contexto
    greenlet y reventaría con MissingGreenlet, fuera del try/except de
    aislamiento por tarea.

    Las reactivaciones se avisan (canal Admin + alertas) DESPUÉS del commit
    del run: nunca se anuncia una oferta que luego no quedó guardada. Un
    fallo del aviso se registra y no afecta al resto de tareas."""
    executed = 0
    tasks = await repo.get_enabled_tasks()
    due_task_ids = [task.id for task in tasks if is_task_due(task, now_local)]
    for task_id in due_task_ids:
        run = None
        try:
            run = await service.run_automatic(task_id)
            executed += 1
        except TaskAlreadyRunningError:
            logger.info("Tarea programada %s ya en curso (p. ej. lanzada desde el panel): se omite", task_id)
        except Exception:
            logger.exception("Fallo al ejecutar la tarea programada %s", task_id)
        await session.commit()
        if run is not None and notifier is not None:
            await notify_reactivations(notifier, run, session)
    return executed


async def notify_reactivations(notifier, run, session) -> None:
    """Avisa de las reactivaciones de un run YA guardado y guarda el antispam.
    Compartida por el worker y por "Ejecutar ahora" del panel: un fallo se
    registra y nunca afecta a lo ya aplicado."""
    deal_ids = reactivated_deal_ids(run)
    if not deal_ids:
        return
    try:
        await notifier.notify(deal_ids, datetime.now(timezone.utc))
        await session.commit()
    except Exception:
        logger.exception("Fallo avisando de %d reactivación(es)", len(deal_ids))
        await session.rollback()


def _build_service(session, settings: Settings) -> tuple[ScheduledTaskRepository, ScheduledTaskService]:
    """Cablea repo + servicio con sus dependencias, aislado de la creación del
    engine/sesión (mismo motivo que `_execute_due_tasks`): así un test puede
    verificar el cableado con un fake de sesión, sin BD real. Antes esto vivía
    inline dentro del try/except de `_run`, que se tragaba cualquier error de
    importación — un `DealRepository` sin importar (import perdido al extraer
    `build_task_handlers` a factory.py) reventaba cada tick automático con
    NameError y la tarea no se ejecutaba nunca sola."""
    repo = ScheduledTaskRepository(session)
    handlers = build_task_handlers(session, settings)
    service = ScheduledTaskService(repo, handlers, session)
    return repo, service


async def _run(settings: Settings) -> int:
    if not settings.database_url:
        logger.error("DATABASE_URL no configurada para el worker de tareas programadas")
        return 0

    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
        connect_args={"server_settings": {"jit": "off"}, "statement_cache_size": 0},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            try:
                repo, service = _build_service(session, settings)

                now_local = datetime.now(timezone.utc).astimezone()
                notifier = build_reactivation_notifier(session, settings)
                executed = await _execute_due_tasks(repo, service, session, now_local, notifier)
                return executed
            except Exception:
                await session.rollback()
                logger.exception("Fallo global del worker de tareas programadas")
                return 0
    finally:
        await engine.dispose()


def run_due_scheduled_tasks(settings: Settings) -> int:
    return asyncio.run(_run(settings))
