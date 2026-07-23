"""Excepciones de dominio del módulo blog."""
from app.core.exceptions import ConflictError, NotFoundError, ValidationError


class BlogPostNotFound(NotFoundError):
    def __init__(self, identifier: str | None = None):
        super().__init__(f"Artículo '{identifier}' no encontrado" if identifier else "Artículo no encontrado")


class BlogCategoryNotFound(NotFoundError):
    def __init__(self, identifier: str | None = None):
        super().__init__(f"Categoría '{identifier}' no encontrada" if identifier else "Categoría no encontrada")


class DuplicateSlugError(ConflictError):
    def __init__(self, slug: str):
        super().__init__(f"Ya existe un artículo con el slug '{slug}'")


class InvalidContentError(ValidationError):
    """El documento Tiptap no cumple el esquema permitido (nodo, marca, url, tamaño...)."""


class PostNotPublishableError(ValidationError):
    """El artículo no cumple las condiciones mínimas para publicarse o programarse."""

    def __init__(self, missing: list[str]):
        super().__init__("El artículo no cumple los requisitos de publicación: " + ", ".join(missing))
        self.payload = {"code": "POST_NOT_PUBLISHABLE", "missing_fields": missing}
