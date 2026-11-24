"""Entrypoint para ejecutar el scheduler en un proceso dedicado.

Uso (contenedor propio en docker-compose, misma imagen que la API):

    command: python -m app.run_scheduler

y en el servicio de la API: SCHEDULER_ENABLED=false. Así los jobs corren
exactamente una vez aunque uvicorn use --workers N (AUDIT_REPORT M-07).
"""

import logging
import signal
import threading

from app.core.bootstrap import register_subscribers
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.modules.deals.application.scheduler import build_deals_scheduler

logger = logging.getLogger(__name__)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, fmt=settings.log_format)
    # Las publicaciones programadas emiten eventos (Instagram se suscribe).
    register_subscribers()
    scheduler, _cleaner = build_deals_scheduler(settings)
    scheduler.start()
    logger.info(
        "Scheduler dedicado en marcha: "
        "mark_expired + verify/publish scheduled (cada 5 min) | "
        "price_check (diario) | clean analytics (03:30)"
    )
    # `docker stop` envía SIGTERM: se espera a que acaben los jobs en curso.
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda _signum, _frame: stop.set())
    try:
        stop.wait()
    except KeyboardInterrupt:
        pass
    scheduler.shutdown(wait=True)
    logger.info("Scheduler dedicado detenido.")


if __name__ == "__main__":
    main()
