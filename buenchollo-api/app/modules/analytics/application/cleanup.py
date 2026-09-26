"""Limpieza periódica de eventos que superan el plazo de conservación."""

import asyncio
import logging

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.modules.analytics.infrastructure.repository import AnalyticsRepository


logger = logging.getLogger(__name__)


async def _run(settings: Settings) -> bool:
    if not settings.database_url:
        logger.error("DATABASE_URL no configurada para limpiar la analítica")
        return False

    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
        connect_args={"server_settings": {"jit": "off"}, "statement_cache_size": 0},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            try:
                await AnalyticsRepository(session).delete_expired(
                    settings.analytics_retention_months
                )
                await session.commit()
                logger.info("Limpieza de analítica completada")
                return True
            except Exception:
                await session.rollback()
                logger.exception("Fallo limpiando eventos antiguos de analítica")
                return False
    finally:
        await engine.dispose()


def run_analytics_cleanup(settings: Settings) -> bool:
    return asyncio.run(_run(settings))
