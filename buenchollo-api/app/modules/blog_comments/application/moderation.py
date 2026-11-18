"""Moderación de comentarios del blog por parte de un administrador."""
from app.modules.blog_comments.domain.exceptions import BlogCommentNotFound
from app.modules.blog_comments.infrastructure.repository import BlogCommentRepository


async def delete_blog_comment_as_admin(repo: BlogCommentRepository, comment_id: str) -> dict:
    """Borra cualquier comentario (sin comprobar autoría). Devuelve los datos
    del comentario borrado para el audit log."""
    comment = await repo.get_by_id(comment_id)
    if not comment:
        raise BlogCommentNotFound()
    post_id = str(comment.blog_post_id)
    author_id = str(comment.user_id)
    await repo.delete(comment)
    return {"blog_post_id": post_id, "author_id": author_id}
