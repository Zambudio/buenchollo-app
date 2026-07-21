"""Entrypoint para ejecutar el scheduler en un proceso dedicado.

Uso (contenedor propio en docker-compose, misma imagen que la API):

    command: python -m app.run_scheduler

y en el servicio de la API: SCHEDULER_ENABLED=false. Así los jobs corren
exactamente una vez aunque uvicorn use --workers N (AUDIT_REPORT M-07).
"""

import logging
import time

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.modules.deals.application.scheduler import build_deals_scheduler

logger = logging.getLogger(__name__)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, fmt=settings.log_format)
    scheduler, cleaner = build_deals_scheduler(settings)
    scheduler.start()
    # Limpieza inicial para no esperar al cron de las 3:00.
    cleaner.clean_expired_deals()
    logger.info(
        "Scheduler dedicado en marcha: "
        "mark_expired + verify/publish scheduled (cada 5 min) | clean (03:00 diario)"
    )
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler dedicado detenido.")


if __name__ == "__main__":
    main()
