from datetime import datetime
from pydantic import BaseModel, Field


class CommentCreate(BaseModel):
    content: str = Field(min_length=2, max_length=1000)
    parent_id: str | None = None


class CommentVoteRequest(BaseModel):
    vote: int = Field(description="1 para upvote, -1 para downvote")


class ProfileLite(BaseModel):
    user_id: str
    display_name: str | None = None
    avatar_url: str | None = None


class CommentItem(BaseModel):
    id: str
    deal_id: str
    user_id: str
    parent_id: str | None = None
    content: str
    votes_up: int
    votes_down: int
    created_at: datetime
    author: ProfileLite | None = None
    my_vote: int = 0


class CommentsListResponse(BaseModel):
    comments: list[CommentItem]
