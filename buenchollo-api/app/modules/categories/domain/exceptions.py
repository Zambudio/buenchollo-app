"""Excepciones de dominio del módulo categories."""
from app.core.exceptions import NotFoundError


class CategoryNotFound(NotFoundError):
    def __init__(self) -> None:
        super().__init__("Category not found")
