"""Excepciones de dominio del módulo comments."""
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError


class CommentNotFound(NotFoundError):
    def __init__(self) -> None:
        super().__init__("Comentario no encontrado")


class NotCommentOwner(ForbiddenError):
    def __init__(self) -> None:
        super().__init__("No puedes modificar este comentario")


class InvalidParentComment(ValidationError):
    def __init__(self) -> None:
        super().__init__("Comentario padre inválido")


class InvalidVote(ValidationError):
    def __init__(self) -> None:
        super().__init__("Voto inválido (debe ser 1 o -1)")
