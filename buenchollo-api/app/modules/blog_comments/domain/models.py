from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, SmallInteger, Integer, String, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.core.database import Base


class BlogComment(Base):
    __tablename__ = "blog_comments"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    blog_post_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("blog_posts.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("blog_comments.id", ondelete="CASCADE"), nullable=True)
    content: Mapped[str] = mapped_column(String, nullable=False)
    votes_up: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    votes_down: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BlogCommentVote(Base):
    __tablename__ = "blog_comment_votes"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    comment_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("blog_comments.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    vote: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("comment_id", "user_id"),)
