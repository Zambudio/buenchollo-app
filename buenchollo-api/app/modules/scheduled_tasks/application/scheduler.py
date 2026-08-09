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
from app.modules.deals.infrastructure.repository import DealRepository
from app.modules.products.infrastructure.amazon_client import AmazonProductClient
from app.modules.scheduled_tasks.application.price_check_handler import PriceCheckHandler
from app.modules.scheduled_tasks.application.scheduled_task_service import (
    ScheduledTaskService,
    is_task_due,
)
from app.modules.scheduled_tasks.infrastructure.repository import ScheduledTaskRepository

logger = logging.getLogger(__name__)


async def _execute_due_tasks(repo, service, now_local: datetime) -> int:
    executed = 0
    tasks = await repo.get_enabled_tasks()
    for task in tasks:
        if not is_task_due(task, now_local):
            continue
        try:
            await service.run_automatic(task.id)
            executed += 1
        except Exception:
            logger.exception("Fallo al ejecutar la tarea programada %s", task.id)
    return executed


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
                repo = ScheduledTaskRepository(session)
                deal_repo = DealRepository(session)
                handler = PriceCheckHandler(AmazonProductClient(settings), deal_repo)
                service = ScheduledTaskService(repo, deal_repo, {"price_check": handler}, session)

                now_local = datetime.now(timezone.utc).astimezone()
                executed = await _execute_due_tasks(repo, service, now_local)
                await session.commit()
                return executed
            except Exception:
                await session.rollback()
                logger.exception("Fallo global del worker de tareas programadas")
                return 0
    finally:
        await engine.dispose()


def run_due_scheduled_tasks(settings: Settings) -> int:
    return asyncio.run(_run(settings))
