"""Excepciones de dominio del módulo scheduled_tasks."""
from app.core.exceptions import ConflictError, NotFoundError


class ScheduledTaskNotFound(NotFoundError):
    def __init__(self, task_id: str | None = None):
        super().__init__(
            f"Tarea programada '{task_id}' no encontrada" if task_id else "Tarea programada no encontrada"
        )


class ScheduledTaskRunNotFound(NotFoundError):
    def __init__(self, run_id: str):
        super().__init__(f"Registro de ejecución '{run_id}' no encontrado")


class RunItemNotFound(NotFoundError):
    def __init__(self, item_id: str):
        super().__init__(f"Elemento de registro '{item_id}' no encontrado")


class ItemAlreadyRestoredError(ConflictError):
    def __init__(self, item_id: str):
        super().__init__(f"El elemento '{item_id}' ya fue restaurado")


class RestoreFailedError(ConflictError):
    def __init__(self, item_id: str):
        super().__init__(
            f"No se pudo restaurar el elemento '{item_id}': "
            "la tienda o categoría original ya no existe"
        )
