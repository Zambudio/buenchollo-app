"""Excepciones de dominio del módulo users."""
from app.core.exceptions import NotFoundError


class ProfileNotFound(NotFoundError):
    def __init__(self) -> None:
        super().__init__("Perfil no encontrado")
