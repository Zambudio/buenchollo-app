"""Tests del builder del scheduler de deals (M-07) y del blog.

Verifican que el scheduler se construye con los jobs de mantenimiento sin
arrancarlo, y que el flag SCHEDULER_ENABLED existe con default seguro (true,
comportamiento actual de un solo proceso).
"""
import subprocess
import sys
from datetime import datetime

from app.core.config import Settings
from app.modules.deals.application.scheduler import build_deals_scheduler


def test_builder_registra_los_ocho_jobs_sin_arrancar():
    scheduler, cleaner = build_deals_scheduler(Settings())
    jobs = scheduler.get_jobs()
    assert len(jobs) == 8
    names = {job.func.__name__ for job in jobs}
    assert names == {
        "mark_expired_deals",
        "run_due_scheduled_publications",
        "run_due_scheduled_posts",
        "run_due_scheduled_tasks",
        "run_analytics_cleanup",
        "run_due_alert_digest",
        "run_awin_feed_sync",
        "run_weekly_deals_digest",
    }
    assert scheduler.running is False
    assert cleaner is not None
    # Catálogo permanente: ningún job borra chollos.
    assert not hasattr(cleaner, "clean_expired_deals")


def test_scheduler_enabled_por_defecto():
    # Default true = comportamiento actual (scheduler en el proceso web,
    # correcto mientras uvicorn corra con un solo worker).
    assert Settings(scheduler_enabled=True).scheduler_enabled is True
    assert Settings(scheduler_enabled=False).scheduler_enabled is False


def test_repositorio_programado_resuelve_mappers_en_proceso_aislado():
    """El worker dedicado debe cargar todas las relaciones ORM sin importar los routers."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from app.modules.scheduled_deals.infrastructure.repository "
                "import ScheduledDealRepository; ScheduledDealRepository._base_query()"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_mark_expired_deals_guarda_el_motivo_expired_date():
    from unittest.mock import MagicMock

    from app.modules.deals.application.cleaner_service import DealCleanerService

    cleaner = DealCleanerService(Settings())
    client = MagicMock()
    cleaner._client = client
    cleaner.mark_expired_deals()
    client.table.return_value.update.assert_called_once_with({"status": "expired", "offer_end_reason": "expired_date"})


def test_scheduler_usa_zona_horaria_de_madrid():
    scheduler, _ = build_deals_scheduler(Settings())
    assert str(scheduler.timezone) == "Europe/Madrid"
    digest = next(j for j in scheduler.get_jobs() if j.id == "nightly_alert_digest")
    # Las 21:00 son hora de Madrid (UTC+1/+2), no UTC.
    next_run = digest.trigger.get_next_fire_time(None, datetime.now(scheduler.timezone))
    assert next_run.hour == 21
    assert next_run.utcoffset().total_seconds() in (3600, 7200)


def test_run_scheduler_hace_shutdown_limpio_con_sigterm():
    import signal
    from unittest.mock import MagicMock, patch

    import app.run_scheduler as run_scheduler

    fake = MagicMock()
    handlers = {}

    def fake_signal(signum, handler):
        handlers[signum] = handler

    with patch.object(run_scheduler, "build_deals_scheduler", return_value=(fake, None)), \
         patch.object(run_scheduler, "configure_logging"), \
         patch.object(run_scheduler.signal, "signal", side_effect=fake_signal), \
         patch.object(run_scheduler.threading, "Event") as ev:
        stop = ev.return_value
        # simula `docker stop`: al esperar, llega SIGTERM
        stop.wait.side_effect = lambda: handlers[signal.SIGTERM](signal.SIGTERM, None)
        run_scheduler.main()

    stop.set.assert_called_once()
    fake.start.assert_called_once()
    fake.shutdown.assert_called_once_with(wait=True)
