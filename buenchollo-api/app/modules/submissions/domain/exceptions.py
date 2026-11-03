from app.core.exceptions import ConflictError, ForbiddenError


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
