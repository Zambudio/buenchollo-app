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
