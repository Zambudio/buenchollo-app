"""Excepciones de dominio del módulo deals."""
from app.core.exceptions import NotFoundError


class DealNotFound(NotFoundError):
    def __init__(self, identifier: str | None = None):
        super().__init__(f"Deal '{identifier}' no encontrado" if identifier else "Deal no encontrado")
