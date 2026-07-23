"""Construcción del scheduler de mantenimiento de deals.

Extraído del lifespan de `main.py` (AUDIT_REPORT M-07) para que el mismo
conjunto de jobs pueda ejecutarse en el proceso web (modo actual, un solo
worker) o en un proceso dedicado (`python -m app.run_scheduler`) cuando
uvicorn pase a múltiples workers — sin duplicar jobs por worker.
"""

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import Settings
from app.modules.deals.application.cleaner_service import DealCleanerService
from app.modules.scheduled_deals.application.publication_worker import run_due_scheduled_publications
from app.modules.blog.application.scheduler import run_due_scheduled_posts


def build_deals_scheduler(settings: Settings) -> tuple[BackgroundScheduler, DealCleanerService]:
    """Crea (sin arrancar) el scheduler con los jobs de mantenimiento.

    Devuelve también el cleaner para que el caller pueda lanzar la limpieza
    inicial al arrancar (no esperar a las 3:00).

    Nota: también registra la publicación programada de artículos del blog.
    El contenedor `buenchollo-scheduler` es el único proceso dedicado a jobs
    periódicos del monolito, así que se reutiliza en vez de crear un
    segundo contenedor/entrypoint solo para el blog.
    """
    scheduler = BackgroundScheduler()
    cleaner = DealCleanerService(settings)
    scheduler.add_job(cleaner.mark_expired_deals, "interval", minutes=5)
    scheduler.add_job(
        run_due_scheduled_publications,
        "cron",
        minute="*/5",
        args=[settings],
        id="publish_scheduled_deals",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(cleaner.clean_expired_deals, "cron", hour=3, minute=0)
    scheduler.add_job(
        run_due_scheduled_posts,
        "cron",
        minute="*/5",
        args=[settings],
        id="publish_scheduled_blog_posts",
        max_instances=1,
        coalesce=True,
    )
    return scheduler, cleaner
