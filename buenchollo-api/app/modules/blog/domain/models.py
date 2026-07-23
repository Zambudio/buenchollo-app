import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, String, Integer, SmallInteger, ForeignKey, DateTime, JSON, Uuid, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base

# Importar Profile para que SQLAlchemy registre 'profiles' antes de resolver la FK author_id
import app.modules.users.domain.models  # noqa: F401


class BlogCategory(Base):
    __tablename__ = "blog_categories"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), default=lambda: datetime.now(timezone.utc))


class BlogPost(Base):
    __tablename__ = "blog_posts"
    __table_args__ = (
        Index("ix_blog_posts_status_published_at", "status", "published_at"),
        Index("ix_blog_posts_category_published_at", "category_id", "published_at"),
        Index("ix_blog_posts_featured_published_at", "is_featured", "published_at"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    excerpt: Mapped[str | None] = mapped_column(String, nullable=True)
    content: Mapped[dict] = mapped_column(JSON, nullable=False, default=lambda: {"type": "doc", "content": []})

    cover_image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    cover_image_alt: Mapped[str | None] = mapped_column(String, nullable=True)

    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)

    category_id: Mapped[str | None] = mapped_column(ForeignKey("blog_categories.id", ondelete="SET NULL"), type_=Uuid(as_uuid=False), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    author_id: Mapped[str | None] = mapped_column(ForeignKey("profiles.user_id", ondelete="SET NULL"), type_=Uuid(as_uuid=False), nullable=True)

    seo_title: Mapped[str | None] = mapped_column(String, nullable=True)
    seo_description: Mapped[str | None] = mapped_column(String, nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(String, nullable=True)
    og_image_url: Mapped[str | None] = mapped_column(String, nullable=True)

    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    votes_up: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    votes_down: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), default=lambda: datetime.now(timezone.utc))

    category = relationship("BlogCategory")


class BlogPostVote(Base):
    __tablename__ = "blog_post_votes"
    __table_args__ = (UniqueConstraint("blog_post_id", "user_id"),)

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    blog_post_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("blog_posts.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    vote: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
