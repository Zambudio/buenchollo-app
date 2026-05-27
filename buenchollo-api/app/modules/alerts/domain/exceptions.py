"""Excepciones de dominio del módulo alerts."""
from app.core.exceptions import NotFoundError


class AlertNotFound(NotFoundError):
    def __init__(self) -> None:
        super().__init__("Alerta no encontrada")
