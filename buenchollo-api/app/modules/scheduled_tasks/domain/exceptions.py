"""Excepciones de dominio del módulo scheduled_tasks."""
from app.core.exceptions import NotFoundError


class ScheduledTaskNotFound(NotFoundError):
    def __init__(self, task_id: str | None = None):
        super().__init__(
            f"Tarea programada '{task_id}' no encontrada" if task_id else "Tarea programada no encontrada"
        )


class ScheduledTaskRunNotFound(NotFoundError):
    def __init__(self, run_id: str):
        super().__init__(f"Registro de ejecución '{run_id}' no encontrado")
