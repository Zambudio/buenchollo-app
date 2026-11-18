"""Excepciones de dominio del módulo alerts."""
from app.core.exceptions import NotFoundError, TooManyRequestsError


class AlertNotFound(NotFoundError):
    def __init__(self) -> None:
        super().__init__("Alerta no encontrada")


class AlertLimitReached(TooManyRequestsError):
    def __init__(self, limit: int) -> None:
        super().__init__(
            f"Has alcanzado el máximo de {limit} alertas. Elimina alguna para crear otra."
        )
