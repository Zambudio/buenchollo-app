from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.modules.comments.domain.models import DealComment, CommentVote


class CommentRepository:
    """Repositorio para comentarios de chollos y sus votos."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_by_deal(self, deal_id: str) -> list[DealComment]:
        result = await self.session.execute(
            select(DealComment)
            .where(DealComment.deal_id == deal_id)
            .order_by(DealComment.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, comment_id: str) -> DealComment | None:
        result = await self.session.execute(
            select(DealComment).where(DealComment.id == comment_id)
        )
        return result.scalars().first()

    async def create(self, deal_id: str, user_id: str, content: str, parent_id: str | None) -> DealComment:
        comment = DealComment(
            deal_id=deal_id,
            user_id=user_id,
            content=content,
            parent_id=parent_id,
        )
        self.session.add(comment)
        await self.session.flush()
        await self.session.refresh(comment)
        return comment

    async def delete(self, comment: DealComment) -> None:
        await self.session.delete(comment)
        await self.session.flush()

    async def upsert_vote(self, comment_id: str, user_id: str, vote: int) -> None:
        stmt = pg_insert(CommentVote).values(
            comment_id=comment_id, user_id=user_id, vote=vote
        ).on_conflict_do_update(
            index_elements=["comment_id", "user_id"],
            set_={"vote": vote},
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def delete_vote(self, comment_id: str, user_id: str) -> None:
        result = await self.session.execute(
            select(CommentVote).where(
                CommentVote.comment_id == comment_id,
                CommentVote.user_id == user_id,
            )
        )
        vote_obj = result.scalars().first()
        if vote_obj:
            await self.session.delete(vote_obj)
            await self.session.flush()

    async def get_user_vote(self, comment_id: str, user_id: str) -> int | None:
        result = await self.session.execute(
            select(CommentVote.vote).where(
                CommentVote.comment_id == comment_id,
                CommentVote.user_id == user_id,
            )
        )
        return result.scalar()

    async def get_user_votes_for_comments(self, comment_ids: list[str], user_id: str) -> dict[str, int]:
        if not comment_ids:
            return {}
        result = await self.session.execute(
            select(CommentVote.comment_id, CommentVote.vote).where(
                CommentVote.comment_id.in_(comment_ids),
                CommentVote.user_id == user_id,
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
