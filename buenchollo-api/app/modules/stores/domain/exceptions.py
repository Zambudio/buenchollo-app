"""Excepciones de dominio del módulo stores."""
from app.core.exceptions import NotFoundError


class StoreNotFound(NotFoundError):
    def __init__(self) -> None:
        super().__init__("Store not found")
