import logging
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.modules.blog_comments.domain.exceptions import (
    BlogCommentNotFound,
    InvalidBlogCommentVote,
    InvalidParentBlogComment,
    NotBlogCommentOwner,
)
from app.modules.blog_comments.infrastructure.repository import BlogCommentRepository
from app.modules.blog_comments.api.schemas import (
    BlogCommentCreate,
    BlogCommentVoteRequest,
    BlogCommentItem,
    BlogCommentsListResponse,
    ProfileLite,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["blog-comments"])


def get_blog_comment_repository(db: AsyncSession = Depends(get_db)) -> BlogCommentRepository:
    return BlogCommentRepository(db)


def _serialize_comment(c, profiles: dict[str, dict], my_votes: dict[str, int]) -> BlogCommentItem:
    prof = profiles.get(str(c.user_id))
    return BlogCommentItem(
        id=str(c.id),
        blog_post_id=str(c.blog_post_id),
        user_id=str(c.user_id),
        parent_id=str(c.parent_id) if c.parent_id else None,
        content=c.content,
        votes_up=c.votes_up,
        votes_down=c.votes_down,
        created_at=c.created_at,
        author=ProfileLite(**prof) if prof else None,
        my_vote=my_votes.get(str(c.id), 0),
    )


@router.get("/blog/posts/{post_id}/comments", response_model=BlogCommentsListResponse)
async def list_comments(
    post_id: str,
    repo: BlogCommentRepository = Depends(get_blog_comment_repository),
):
    """Lista pública de comentarios de un artículo. Sin votos del usuario."""
    comments = await repo.list_by_post(post_id)
    user_ids = list({str(c.user_id) for c in comments})
    profiles = await repo.get_profiles_for_users(user_ids)
    return BlogCommentsListResponse(
        comments=[_serialize_comment(c, profiles, {}) for c in comments]
    )


@router.get("/blog/posts/{post_id}/comments/with-my-votes", response_model=BlogCommentsListResponse)
async def list_comments_with_my_votes(
    post_id: str,
    repo: BlogCommentRepository = Depends(get_blog_comment_repository),
    current_user=Depends(get_current_user),
):
    """Lista de comentarios incluyendo el voto del usuario autenticado en cada uno."""
    comments = await repo.list_by_post(post_id)
    user_ids = list({str(c.user_id) for c in comments})
    comment_ids = [str(c.id) for c in comments]
    profiles = await repo.get_profiles_for_users(user_ids)
    my_votes = await repo.get_user_votes_for_comments(comment_ids, str(current_user.id))
    return BlogCommentsListResponse(
        comments=[_serialize_comment(c, profiles, my_votes) for c in comments]
    )


@router.post(
    "/blog/posts/{post_id}/comments",
    response_model=BlogCommentItem,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")  # anti-spam de comentarios
async def create_comment(
    request: Request,
    post_id: str,
    payload: BlogCommentCreate,
    repo: BlogCommentRepository = Depends(get_blog_comment_repository),
    current_user=Depends(get_current_user),
):
    if payload.parent_id:
        parent = await repo.get_by_id(payload.parent_id)
        if not parent or str(parent.blog_post_id) != post_id:
            raise InvalidParentBlogComment()

    comment = await repo.create(
        blog_post_id=post_id,
        user_id=str(current_user.id),
        content=payload.content.strip(),
        parent_id=payload.parent_id,
    )
    profiles = await repo.get_profiles_for_users([str(current_user.id)])
    return _serialize_comment(comment, profiles, {})


@router.delete("/blog/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: str,
    repo: BlogCommentRepository = Depends(get_blog_comment_repository),
    current_user=Depends(get_current_user),
):
    comment = await repo.get_by_id(comment_id)
    if not comment:
        raise BlogCommentNotFound()
    if str(comment.user_id) != str(current_user.id):
        raise NotBlogCommentOwner()
    await repo.delete(comment)


@router.post("/blog/comments/{comment_id}/vote")
async def vote_comment(
    comment_id: str,
    payload: BlogCommentVoteRequest,
    repo: BlogCommentRepository = Depends(get_blog_comment_repository),
    current_user=Depends(get_current_user),
) -> dict:
    if payload.vote not in (1, -1):
        raise InvalidBlogCommentVote()
    comment = await repo.get_by_id(comment_id)
    if not comment:
        raise BlogCommentNotFound()

    user_id = str(current_user.id)
    current = await repo.get_user_vote(comment_id, user_id)
    if current == payload.vote:
        await repo.delete_vote(comment_id, user_id)
        return {"my_vote": 0}
    await repo.upsert_vote(comment_id, user_id, payload.vote)
    return {"my_vote": payload.vote}
