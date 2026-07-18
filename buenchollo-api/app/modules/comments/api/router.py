import logging
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.modules.comments.domain.exceptions import (
    CommentNotFound,
    InvalidParentComment,
    InvalidVote,
    NotCommentOwner,
)
from app.modules.comments.infrastructure.repository import CommentRepository
from app.modules.comments.api.schemas import (
    CommentCreate,
    CommentVoteRequest,
    CommentItem,
    CommentsListResponse,
    ProfileLite,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["comments"])


def get_comment_repository(db: AsyncSession = Depends(get_db)) -> CommentRepository:
    return CommentRepository(db)


def _serialize_comment(c, profiles: dict[str, dict], my_votes: dict[str, int]) -> CommentItem:
    prof = profiles.get(str(c.user_id))
    return CommentItem(
        id=str(c.id),
        deal_id=str(c.deal_id),
        user_id=str(c.user_id),
        parent_id=str(c.parent_id) if c.parent_id else None,
        content=c.content,
        votes_up=c.votes_up,
        votes_down=c.votes_down,
        created_at=c.created_at,
        author=ProfileLite(**prof) if prof else None,
        my_vote=my_votes.get(str(c.id), 0),
    )


@router.get("/deals/{deal_id}/comments", response_model=CommentsListResponse)
async def list_comments(
    deal_id: str,
    repo: CommentRepository = Depends(get_comment_repository),
):
    """Lista pública de comentarios de un chollo. Sin votos del usuario."""
    comments = await repo.list_by_deal(deal_id)
    user_ids = list({str(c.user_id) for c in comments})
    profiles = await repo.get_profiles_for_users(user_ids)
    return CommentsListResponse(
        comments=[_serialize_comment(c, profiles, {}) for c in comments]
    )


@router.get("/deals/{deal_id}/comments/with-my-votes", response_model=CommentsListResponse)
async def list_comments_with_my_votes(
    deal_id: str,
    repo: CommentRepository = Depends(get_comment_repository),
    current_user=Depends(get_current_user),
):
    """Lista de comentarios incluyendo el voto del usuario autenticado en cada uno."""
    comments = await repo.list_by_deal(deal_id)
    user_ids = list({str(c.user_id) for c in comments})
    comment_ids = [str(c.id) for c in comments]
    profiles = await repo.get_profiles_for_users(user_ids)
    my_votes = await repo.get_user_votes_for_comments(comment_ids, str(current_user.id))
    return CommentsListResponse(
        comments=[_serialize_comment(c, profiles, my_votes) for c in comments]
    )


@router.post("/deals/{deal_id}/comments", response_model=CommentItem, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")  # anti-spam de comentarios
async def create_comment(
    request: Request,
    deal_id: str,
    payload: CommentCreate,
    repo: CommentRepository = Depends(get_comment_repository),
    current_user=Depends(get_current_user),
):
    if payload.parent_id:
        parent = await repo.get_by_id(payload.parent_id)
        if not parent or str(parent.deal_id) != deal_id:
            raise InvalidParentComment()

    comment = await repo.create(
        deal_id=deal_id,
        user_id=str(current_user.id),
        content=payload.content.strip(),
        parent_id=payload.parent_id,
    )
    await repo.recalculate_comment_count(deal_id)
    profiles = await repo.get_profiles_for_users([str(current_user.id)])
    return _serialize_comment(comment, profiles, {})


@router.delete("/deals/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: str,
    repo: CommentRepository = Depends(get_comment_repository),
    current_user=Depends(get_current_user),
):
    comment = await repo.get_by_id(comment_id)
    if not comment:
        raise CommentNotFound()
    if str(comment.user_id) != str(current_user.id):
        raise NotCommentOwner()
    deal_id = str(comment.deal_id)
    await repo.delete(comment)
    await repo.recalculate_comment_count(deal_id)


@router.post("/deals/comments/{comment_id}/vote")
async def vote_comment(
    comment_id: str,
    payload: CommentVoteRequest,
    repo: CommentRepository = Depends(get_comment_repository),
    current_user=Depends(get_current_user),
) -> dict:
    if payload.vote not in (1, -1):
        raise InvalidVote()
    comment = await repo.get_by_id(comment_id)
    if not comment:
        raise CommentNotFound()

    user_id = str(current_user.id)
    current = await repo.get_user_vote(comment_id, user_id)
    if current == payload.vote:
        await repo.delete_vote(comment_id, user_id)
        return {"my_vote": 0}
    await repo.upsert_vote(comment_id, user_id, payload.vote)
    return {"my_vote": payload.vote}
