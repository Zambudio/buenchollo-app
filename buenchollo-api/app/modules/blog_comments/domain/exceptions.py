"""Excepciones de dominio del módulo blog_comments."""
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError


class BlogCommentNotFound(NotFoundError):
    def __init__(self) -> None:
        super().__init__("Comentario no encontrado")


class NotBlogCommentOwner(ForbiddenError):
    def __init__(self) -> None:
        super().__init__("No puedes modificar este comentario")


class InvalidParentBlogComment(ValidationError):
    def __init__(self) -> None:
        super().__init__("Comentario padre inválido")


class InvalidBlogCommentVote(ValidationError):
    def __init__(self) -> None:
        super().__init__("Voto inválido (debe ser 1 o -1)")
