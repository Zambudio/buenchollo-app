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
from app.modules.scheduled_tasks.application.scheduler import run_due_scheduled_tasks
from app.modules.analytics.application.cleanup import run_analytics_cleanup
from app.modules.emails.application.digest_worker import run_due_alert_digest
from app.modules.affiliates.application.feed_sync_job import run_awin_feed_sync
from app.modules.telegram.application.weekly_digest import run_weekly_deals_digest

from app.core.jobs import SCHEDULER_TIMEZONE


def build_deals_scheduler(settings: Settings) -> tuple[BackgroundScheduler, DealCleanerService]:
    """Crea (sin arrancar) el scheduler con los jobs de mantenimiento.

    Devuelve también el cleaner (caducidad por fecha y activación de
    programados). Ningún job borra chollos: catálogo permanente.

    Nota: también registra la publicación programada de artículos del blog.
    El contenedor `buenchollo-scheduler` es el único proceso dedicado a jobs
    periódicos del monolito, así que se reutiliza en vez de crear un
    segundo contenedor/entrypoint solo para el blog.
    """
    scheduler = BackgroundScheduler(timezone=SCHEDULER_TIMEZONE)
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
    scheduler.add_job(
        run_due_scheduled_posts,
        "cron",
        minute="*/5",
        args=[settings],
        id="publish_scheduled_blog_posts",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        run_due_scheduled_tasks,
        "interval",
        hours=1,
        args=[settings],
        id="run_scheduled_tasks",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        run_analytics_cleanup,
        "cron",
        hour=3,
        minute=30,
        args=[settings],
        id="cleanup_analytics",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        run_due_alert_digest,
        "cron",
        hour=21,
        minute=0,
        args=[settings],
        id="nightly_alert_digest",
        max_instances=1,
        coalesce=True,
    )
    # Feeds de producto Awin seleccionados: una vez al día (la lista de feeds
    # dice si cambió cada uno; sin credenciales de feeds el job no hace nada).
    scheduler.add_job(
        run_awin_feed_sync,
        "cron",
        hour=5,
        minute=17,
        args=[settings],
        id="sync_awin_feeds",
        max_instances=1,
        coalesce=True,
    )
    # «Los chollos de la semana» al canal Admin: domingos a las 22:30. Si el
    # contenedor estaba parado a esa hora, se envía al arrancar dentro de la
    # hora siguiente (misfire_grace_time); después ya no, para no mandar un
    # resumen de domingo el lunes.
    scheduler.add_job(
        run_weekly_deals_digest,
        "cron",
        day_of_week="sun",
        hour=22,
        minute=30,
        args=[settings],
        id="weekly_deals_digest",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    return scheduler, cleaner
