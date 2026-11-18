"""Limpieza periódica de eventos que superan el plazo de conservación."""

import asyncio
import logging

from app.core.config import Settings
from app.core.jobs import job_session
from app.modules.analytics.infrastructure.repository import AnalyticsRepository


logger = logging.getLogger(__name__)


async def _run(settings: Settings) -> bool:
    if not settings.database_url:
        logger.error("DATABASE_URL no configurada para limpiar la analítica")
        return False

    async with job_session(settings) as session:
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


def run_analytics_cleanup(settings: Settings) -> bool:
    return asyncio.run(_run(settings))
