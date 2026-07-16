"""Tests del builder del scheduler de deals (M-07).

Verifican que el scheduler se construye con los 3 jobs de mantenimiento sin
arrancarlo, y que el flag SCHEDULER_ENABLED existe con default seguro (true,
comportamiento actual de un solo proceso).
"""
from app.core.config import Settings
from app.modules.deals.application.scheduler import build_deals_scheduler


def test_builder_registra_los_tres_jobs_sin_arrancar():
    scheduler, cleaner = build_deals_scheduler(Settings())
    jobs = scheduler.get_jobs()
    assert len(jobs) == 3
    names = {job.func.__name__ for job in jobs}
    assert names == {"mark_expired_deals", "activate_scheduled_deals", "clean_expired_deals"}
    assert scheduler.running is False
    assert cleaner is not None


def test_scheduler_enabled_por_defecto():
    # Default true = comportamiento actual (scheduler en el proceso web,
    # correcto mientras uvicorn corra con un solo worker).
    assert Settings(scheduler_enabled=True).scheduler_enabled is True
    assert Settings(scheduler_enabled=False).scheduler_enabled is False
