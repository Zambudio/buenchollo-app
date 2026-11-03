from app.core.exceptions import ForbiddenError


class ProfileIncompleteError(ForbiddenError):
    """El usuario no ha completado su perfil (nombre público)."""

    def __init__(self, message: str = "Completa tu perfil para publicar chollos.") -> None:
        super().__init__(message)
        self.payload = {"code": "PROFILE_INCOMPLETE"}
