from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.modules.blog_comments.domain.models import BlogComment, BlogCommentVote


class BlogCommentRepository:
    """Repositorio para comentarios de artículos del blog y sus votos."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_by_post(self, blog_post_id: str) -> list[BlogComment]:
        """Comentarios ordenados por score (votos_up - votos_down) DESC, y por
        fecha de creación DESC como desempate. El frontend separa raíces e hijos."""
        score = (BlogComment.votes_up - BlogComment.votes_down).label("score")
        result = await self.session.execute(
            select(BlogComment)
            .where(BlogComment.blog_post_id == blog_post_id)
            .order_by(score.desc(), BlogComment.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, comment_id: str) -> BlogComment | None:
        result = await self.session.execute(
            select(BlogComment).where(BlogComment.id == comment_id)
        )
        return result.scalars().first()

    async def create(self, blog_post_id: str, user_id: str, content: str, parent_id: str | None) -> BlogComment:
        comment = BlogComment(
            blog_post_id=blog_post_id,
            user_id=user_id,
            content=content,
            parent_id=parent_id,
        )
        self.session.add(comment)
        await self.session.flush()
        await self.session.refresh(comment)
        return comment

    async def delete(self, comment: BlogComment) -> None:
        await self.session.delete(comment)
        await self.session.flush()

    async def upsert_vote(self, comment_id: str, user_id: str, vote: int) -> None:
        stmt = pg_insert(BlogCommentVote).values(
            comment_id=comment_id, user_id=user_id, vote=vote
        ).on_conflict_do_update(
            index_elements=["comment_id", "user_id"],
            set_={"vote": vote},
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def delete_vote(self, comment_id: str, user_id: str) -> None:
        result = await self.session.execute(
            select(BlogCommentVote).where(
                BlogCommentVote.comment_id == comment_id,
                BlogCommentVote.user_id == user_id,
            )
        )
        vote_obj = result.scalars().first()
        if vote_obj:
            await self.session.delete(vote_obj)
            await self.session.flush()

    async def recalculate_votes(self, comment_id: str) -> dict:
        """Recalcula votes_up/votes_down desde blog_comment_votes y actualiza
        el comentario. Se llama explícitamente desde el router tras cada voto
        (no depende del trigger `blog_comment_votes_recalc` de la migración,
        que el esquema efímero de test del CI no crea al partir solo del
        grafo ORM)."""
        row = (await self.session.execute(
            text("""
                UPDATE blog_comments SET
                    votes_up   = (SELECT COUNT(*) FROM blog_comment_votes WHERE comment_id = CAST(:id AS uuid) AND vote = 1),
                    votes_down = (SELECT COUNT(*) FROM blog_comment_votes WHERE comment_id = CAST(:id AS uuid) AND vote = -1)
                WHERE id = CAST(:id AS uuid)
                RETURNING votes_up, votes_down
            """),
            {"id": comment_id},
        )).mappings().first()
        return dict(row) if row else {"votes_up": 0, "votes_down": 0}

    async def get_user_vote(self, comment_id: str, user_id: str) -> int | None:
        result = await self.session.execute(
            select(BlogCommentVote.vote).where(
                BlogCommentVote.comment_id == comment_id,
                BlogCommentVote.user_id == user_id,
            )
        )
        return result.scalar()

    async def get_user_votes_for_comments(self, comment_ids: list[str], user_id: str) -> dict[str, int]:
        if not comment_ids:
            return {}
        result = await self.session.execute(
            select(BlogCommentVote.comment_id, BlogCommentVote.vote).where(
                BlogCommentVote.comment_id.in_(comment_ids),
                BlogCommentVote.user_id == user_id,
            )
        )
        return {str(cid): vote for cid, vote in result.all()}

    async def get_profiles_for_users(self, user_ids: list[str]) -> dict[str, dict]:
        """Devuelve perfiles públicos (user_id → {display_name, avatar_url}) para los user_ids dados."""
        if not user_ids:
            return {}
        result = await self.session.execute(
            text(
                "SELECT user_id::text, display_name, avatar_url "
                "FROM profiles WHERE user_id = ANY(CAST(:uids AS uuid[]))"
            ),
            {"uids": user_ids},
        )
        return {
            row[0]: {"user_id": row[0], "display_name": row[1], "avatar_url": row[2]}
            for row in result.fetchall()
        }
