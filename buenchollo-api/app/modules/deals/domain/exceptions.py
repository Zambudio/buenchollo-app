"""Excepciones de dominio del módulo deals."""
from app.core.exceptions import ConflictError, NotFoundError


class DealNotFound(NotFoundError):
    def __init__(self, identifier: str | None = None):
        super().__init__(f"Deal '{identifier}' no encontrado" if identifier else "Deal no encontrado")


class DuplicateDealError(ConflictError):
    """Existe otro deal con el mismo external_id (ASIN). → 409.

    Adjunta `payload` con los datos del deal existente para que el
    frontend pueda ofrecer al admin las opciones de sobrescribir o
    saltar a editar el existente. El handler global de `main.py`
    fusiona `payload` en el cuerpo JSON de la respuesta.
    """

    def __init__(self, existing_id: str, existing_slug: str, existing_title: str):
        super().__init__(f"Ya existe un chollo con este ASIN: '{existing_title}'")
        self.payload = {
            "code": "DUPLICATE_DEAL",
            "existing_deal": {
                "id": existing_id,
                "slug": existing_slug,
                "title": existing_title,
            },
        }
