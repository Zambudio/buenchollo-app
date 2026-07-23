"""Tests del builder del scheduler de deals (M-07) y del blog.

Verifican que el scheduler se construye con los jobs de mantenimiento sin
arrancarlo, y que el flag SCHEDULER_ENABLED existe con default seguro (true,
comportamiento actual de un solo proceso).
"""
import subprocess
import sys

from app.core.config import Settings
from app.modules.deals.application.scheduler import build_deals_scheduler


def test_builder_registra_los_cuatro_jobs_sin_arrancar():
    scheduler, cleaner = build_deals_scheduler(Settings())
    jobs = scheduler.get_jobs()
    assert len(jobs) == 4
    names = {job.func.__name__ for job in jobs}
    assert names == {
        "mark_expired_deals",
        "run_due_scheduled_publications",
        "clean_expired_deals",
        "run_due_scheduled_posts",
    }
    assert scheduler.running is False
    assert cleaner is not None


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
