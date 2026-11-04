from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    ServiceUnavailableError,
    ValidationError,
)


class ProfileIncompleteError(ForbiddenError):
    """El usuario no ha completado su perfil (nombre público)."""

    def __init__(self, message: str = "Completa tu perfil para publicar chollos.") -> None:
        super().__init__(message)
        self.payload = {"code": "PROFILE_INCOMPLETE"}


class SubmissionConflictError(ConflictError):
    """La propuesta choca con un chollo publicado, próximo o ya en revisión."""

    def __init__(self, reason: str, existing_deal: dict | None = None) -> None:
        messages = {
            "published": "Este chollo ya está publicado.",
            "upcoming": "Este chollo ya está programado para publicarse.",
            "in_review": "Este chollo ya está en revisión.",
        }
        super().__init__(messages.get(reason, "Este chollo ya existe."))
        self.payload = {
            "code": "SUBMISSION_DUPLICATE",
            "reason": reason,
            "existing_deal": existing_deal,
        }


class InvalidImageError(ValidationError):
    """La imagen subida o descargada no es válida o supera los límites."""

    def __init__(self, message: str = "El archivo no es una imagen válida") -> None:
        super().__init__(message)


class ImageStorageUnavailableError(ServiceUnavailableError):
    """El almacenamiento de imágenes no está disponible."""

    def __init__(
        self, message: str = "No se pudo guardar la imagen. Inténtalo de nuevo en unos minutos."
    ) -> None:
        super().__init__(message)


class SubmissionNotPendingError(ConflictError):
    """La propuesta ya no está pendiente (aprobada, rechazada o retirada)."""

    def __init__(self, message: str = "La propuesta ya no está pendiente de revisión") -> None:
        super().__init__(message)


class AsinMismatchError(ValidationError):
    """El ASIN indicado no coincide con el del enlace de afiliado. → 422."""

    http_status = 422

    def __init__(self, external_id: str, url_asin: str) -> None:
        super().__init__(
            f"El ASIN indicado ({external_id}) no coincide con el del enlace ({url_asin}). "
            "Corrige el ASIN o el enlace antes de publicar."
        )
