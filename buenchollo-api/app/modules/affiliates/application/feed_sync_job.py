"""Ejecución de la sincronización de feeds fuera de las peticiones del editor:
desde el panel (BackgroundTasks), el scheduler diario o el script CLI.

Mismo patrón que `scheduled_tasks/application/scheduler.py`: engine propio con
NullPool. Un advisory lock de transacción (`pg_try_advisory_xact_lock`), en
una conexión aparte cuya transacción dura toda la sincronización, evita dos a
la vez (API y contenedor scheduler). Es de transacción y no de sesión para que
con PgBouncer en modo transacción nunca quede un lock huérfano: se libera solo
al terminar (o caerse) esa transacción.
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.modules.affiliates.application.feed_sync import AwinFeedSync
from app.modules.affiliates.infrastructure.awin_client import AwinClient
from app.modules.affiliates.infrastructure.repository import AffiliateRepository

logger = logging.getLogger(__name__)

_LOCK_KEY = 0x0BC7_A515  # constante arbitraria para el advisory lock


async def run_awin_feed_sync_async(
    settings: Settings, *, program_id: str | None = None, force: bool = False, jitter: bool = False
) -> list[dict]:
    if not settings.database_url:
        return [{"status": "error", "message": "DATABASE_URL no configurada"}]
    client = AwinClient(settings)
    if not client.feeds_configured:
        return [{"status": "not_configured", "message": "Faltan AWIN_PUBLISHER_ID / AWIN_FEED_API_KEY."}]
    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
        connect_args={"server_settings": {"jit": "off"}, "statement_cache_size": 0},
    )
    try:
        async with engine.connect() as lock_conn:
            got = (await lock_conn.execute(text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": _LOCK_KEY})).scalar()
            if not got:
                return [{"status": "already_running", "message": "Ya hay una sincronización en curso."}]
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                report = await AwinFeedSync(AffiliateRepository(session), client).run(
                    program_id=program_id, force=force, jitter=jitter
                )
            await lock_conn.rollback()  # libera el lock
            logger.info("Sincronización de feeds Awin: %s", report)
            return report
    except Exception:
        logger.exception("Fallo global de la sincronización de feeds Awin")
        return [{"status": "error", "message": "Fallo global de la sincronización (ver logs)."}]
    finally:
        client.http.close()
        await engine.dispose()


def run_awin_feed_sync(settings: Settings) -> list[dict]:
    """Job síncrono para APScheduler. Sin credenciales de feeds no hace nada."""
    if not (settings.awin_publisher_id and settings.awin_feed_api_key):
        return []
    return asyncio.run(run_awin_feed_sync_async(settings, jitter=True))
