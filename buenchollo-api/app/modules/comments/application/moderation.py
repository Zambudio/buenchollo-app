"""Moderación de comentarios de chollos por parte de un administrador."""
from app.modules.comments.domain.exceptions import CommentNotFound
from app.modules.comments.infrastructure.repository import CommentRepository


async def delete_comment_as_admin(repo: CommentRepository, comment_id: str) -> dict:
    """Borra cualquier comentario (sin comprobar autoría) y recalcula el
    contador del chollo. Devuelve los datos del comentario borrado para el audit log."""
    comment = await repo.get_by_id(comment_id)
    if not comment:
        raise CommentNotFound()
    deal_id = str(comment.deal_id)
    author_id = str(comment.user_id)
    await repo.delete(comment)
    await repo.recalculate_comment_count(deal_id)
    return {"deal_id": deal_id, "author_id": author_id}
