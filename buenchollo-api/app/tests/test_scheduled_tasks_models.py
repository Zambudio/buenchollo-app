"""Verifica que los modelos de scheduled_tasks resuelven sus relaciones
(FK a profiles) en un proceso aislado, igual que scheduled_deals
(test_scheduler_builder.py::test_repositorio_programado_resuelve_mappers_en_proceso_aislado)."""
import subprocess
import sys


def test_scheduled_tasks_resuelve_mappers_en_proceso_aislado():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from app.modules.scheduled_tasks.domain.models import ScheduledTask, ScheduledTaskRun, ScheduledTaskRunItem; "
                "from sqlalchemy import inspect; "
                "inspect(ScheduledTask); inspect(ScheduledTaskRun); inspect(ScheduledTaskRunItem)"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_tablenames():
    from app.modules.scheduled_tasks.domain.models import (
        ScheduledTask,
        ScheduledTaskRun,
        ScheduledTaskRunItem,
    )

    assert ScheduledTask.__tablename__ == "scheduled_tasks"
    assert ScheduledTaskRun.__tablename__ == "scheduled_task_runs"
    assert ScheduledTaskRunItem.__tablename__ == "scheduled_task_run_items"
