from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import unquote

from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.application.service import PageViewEvent
from app.modules.analytics.domain.models import AnalyticsBlogDailyView, AnalyticsEvent
from app.modules.blog.domain.models import BlogPost


def _blog_slug_from_path(path: str) -> str | None:
    parts = path.strip("/").split("/")
    if len(parts) != 2 or parts[0] != "blog" or not parts[1]:
        return None
    return unquote(parts[1])


class AnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _published_blog_post(self, path: str) -> BlogPost | None:
        slug = _blog_slug_from_path(path)
        if not slug:
            return None
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(BlogPost).where(
                BlogPost.slug == slug,
                BlogPost.status == "published",
                BlogPost.published_at.is_not(None),
                BlogPost.published_at <= now,
            )
        )
        return result.scalars().first()

    async def record_page_view(self, event: PageViewEvent) -> int | None:
        post = await self._published_blog_post(event.path)
        self.session.add(
            AnalyticsEvent(
                visitor_hash=event.visitor_hash,
                session_hash=event.session_hash,
                path=event.path,
                blog_post_id=post.id if post else None,
                source=event.source,
                source_detail=event.source_detail,
                medium=event.medium,
                campaign=event.campaign,
                referrer_host=event.referrer_host,
            )
        )

        if not post:
            await self.session.flush()
            return None

        inserted = (
            await self.session.execute(
                pg_insert(AnalyticsBlogDailyView)
                .values(
                    blog_post_id=post.id,
                    visitor_hash=event.visitor_hash,
                    view_date=datetime.now(timezone.utc).date(),
                )
                .on_conflict_do_nothing(
                    index_elements=["blog_post_id", "visitor_hash", "view_date"]
                )
                .returning(AnalyticsBlogDailyView.blog_post_id)
            )
        ).scalar_one_or_none()

        if inserted:
            return int(
                (
                    await self.session.execute(
                        update(BlogPost)
                        .where(BlogPost.id == post.id)
                        .values(view_count=BlogPost.view_count + 1)
                        .returning(BlogPost.view_count)
                    )
                ).scalar_one()
            )

        return int(post.view_count)

    async def delete_expired(self, retention_months: int) -> None:
        await self.session.execute(
            text(
                """
                DELETE FROM analytics_events
                WHERE occurred_at < now() - make_interval(months => :retention_months)
                """
            ),
            {"retention_months": retention_months},
        )
        await self.session.execute(
            text(
                """
                DELETE FROM analytics_blog_daily_views
                WHERE created_at < now() - make_interval(months => :retention_months)
                """
            ),
            {"retention_months": retention_months},
        )

    async def get_overview(self, days: int) -> dict:
        start_at = datetime.now(timezone.utc) - timedelta(days=days)
        params = {"start_at": start_at}

        totals_row = (
            await self.session.execute(
                text(
                    """
                    SELECT
                      COUNT(*)::bigint AS page_views,
                      COUNT(DISTINCT visitor_hash)::bigint AS unique_visitors,
                      COUNT(DISTINCT session_hash)::bigint AS sessions,
                      COUNT(*) FILTER (WHERE blog_post_id IS NOT NULL)::bigint AS blog_views,
                      COUNT(DISTINCT visitor_hash) FILTER (WHERE source = 'telegram')::bigint
                        AS telegram_visitors,
                      COUNT(DISTINCT visitor_hash) FILTER (WHERE source = 'organic')::bigint
                        AS organic_visitors,
                      COUNT(DISTINCT visitor_hash) FILTER (
                        WHERE source = 'telegram' AND blog_post_id IS NOT NULL
                      )::bigint AS telegram_blog_visitors
                    FROM analytics_events
                    WHERE occurred_at >= :start_at
                    """
                ),
                params,
            )
        ).mappings().one()

        timeseries_rows = (
            await self.session.execute(
                text(
                    """
                    SELECT occurred_at::date AS date,
                           COUNT(*)::bigint AS views,
                           COUNT(DISTINCT visitor_hash)::bigint AS visitors
                    FROM analytics_events
                    WHERE occurred_at >= :start_at
                    GROUP BY occurred_at::date
                    ORDER BY occurred_at::date
                    """
                ),
                params,
            )
        ).mappings().all()

        source_rows = (
            await self.session.execute(
                text(
                    """
                    SELECT source,
                           COUNT(*)::bigint AS views,
                           COUNT(DISTINCT visitor_hash)::bigint AS visitors,
                           COUNT(DISTINCT session_hash)::bigint AS sessions,
                           COUNT(*) FILTER (WHERE blog_post_id IS NOT NULL)::bigint AS blog_views
                    FROM analytics_events
                    WHERE occurred_at >= :start_at
                    GROUP BY source
                    ORDER BY visitors DESC, source
                    """
                ),
                params,
            )
        ).mappings().all()

        page_rows = (
            await self.session.execute(
                text(
                    """
                    SELECT path,
                           COUNT(*)::bigint AS views,
                           COUNT(DISTINCT visitor_hash)::bigint AS visitors
                    FROM analytics_events
                    WHERE occurred_at >= :start_at
                    GROUP BY path
                    ORDER BY views DESC, path
                    LIMIT 10
                    """
                ),
                params,
            )
        ).mappings().all()

        article_rows = (
            await self.session.execute(
                text(
                    """
                    SELECT p.id::text AS id, p.title, p.slug, p.view_count,
                           COUNT(e.id)::bigint AS views,
                           COUNT(DISTINCT e.visitor_hash)::bigint AS visitors
                    FROM analytics_events e
                    JOIN blog_posts p ON p.id = e.blog_post_id
                    WHERE e.occurred_at >= :start_at
                    GROUP BY p.id, p.title, p.slug, p.view_count
                    ORDER BY views DESC, p.title
                    LIMIT 10
                    """
                ),
                params,
            )
        ).mappings().all()

        totals = {key: int(value or 0) for key, value in totals_row.items()}
        telegram_visitors = totals["telegram_visitors"]
        totals["telegram_to_blog_rate"] = round(
            (totals["telegram_blog_visitors"] / telegram_visitors * 100)
            if telegram_visitors
            else 0,
            1,
        )
        return {
            "days": days,
            "totals": totals,
            "timeseries": [
                {"date": row["date"], "views": int(row["views"]), "visitors": int(row["visitors"])}
                for row in timeseries_rows
            ],
            "sources": [
                {
                    "source": row["source"],
                    "views": int(row["views"]),
                    "visitors": int(row["visitors"]),
                    "sessions": int(row["sessions"]),
                    "blog_views": int(row["blog_views"]),
                }
                for row in source_rows
            ],
            "top_pages": [dict(row) for row in page_rows],
            "top_articles": [dict(row) for row in article_rows],
        }
