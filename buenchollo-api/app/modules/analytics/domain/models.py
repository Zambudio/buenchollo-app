from datetime import date, datetime, timezone

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"
    __table_args__ = (
        CheckConstraint(
            "source IN ('telegram', 'organic', 'referral', 'direct')",
            name="ck_analytics_events_source",
        ),
        CheckConstraint("char_length(path) BETWEEN 1 AND 500", name="ck_analytics_events_path"),
        Index("ix_analytics_events_occurred_at", "occurred_at"),
        Index("ix_analytics_events_source_occurred_at", "source", "occurred_at"),
        Index("ix_analytics_events_visitor_occurred_at", "visitor_hash", "occurred_at"),
        Index("ix_analytics_events_session_occurred_at", "session_hash", "occurred_at"),
        Index("ix_analytics_events_blog_occurred_at", "blog_post_id", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc)
    )
    visitor_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    session_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    blog_post_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("blog_posts.id", ondelete="SET NULL"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    source_detail: Mapped[str] = mapped_column(String(100), nullable=False)
    medium: Mapped[str] = mapped_column(String(50), nullable=False)
    campaign: Mapped[str | None] = mapped_column(String(100), nullable=True)
    referrer_host: Mapped[str | None] = mapped_column(String(253), nullable=True)


class AnalyticsBlogDailyView(Base):
    __tablename__ = "analytics_blog_daily_views"
    __table_args__ = (
        Index("ix_analytics_blog_daily_views_date", "view_date"),
        Index("ix_analytics_blog_daily_views_visitor_date", "visitor_hash", "view_date"),
    )

    blog_post_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("blog_posts.id", ondelete="CASCADE"), primary_key=True
    )
    visitor_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    view_date: Mapped[date] = mapped_column(Date, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc)
    )
