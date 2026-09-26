from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


AnalyticsSource = Literal["telegram", "organic", "referral", "direct"]


class TrackPageViewRequest(BaseModel):
    visitor_id: UUID
    session_id: UUID
    path: str = Field(min_length=1, max_length=500, pattern=r"^/")
    source: AnalyticsSource
    source_detail: str = Field(min_length=1, max_length=100)
    medium: str = Field(min_length=1, max_length=50)
    campaign: str | None = Field(default=None, max_length=100)
    referrer_host: str | None = Field(default=None, max_length=253)


class TrackPageViewResponse(BaseModel):
    accepted: bool
    blog_view_count: int | None = None


class AnalyticsTotalsResponse(BaseModel):
    page_views: int
    unique_visitors: int
    sessions: int
    blog_views: int
    telegram_visitors: int
    organic_visitors: int
    telegram_blog_visitors: int
    telegram_to_blog_rate: float


class AnalyticsDayResponse(BaseModel):
    date: date
    views: int
    visitors: int


class AnalyticsSourceResponse(BaseModel):
    source: AnalyticsSource
    views: int
    visitors: int
    sessions: int
    blog_views: int


class AnalyticsPageResponse(BaseModel):
    path: str
    views: int
    visitors: int


class AnalyticsArticleResponse(BaseModel):
    id: str
    title: str
    slug: str
    view_count: int
    views: int
    visitors: int


class AnalyticsOverviewResponse(BaseModel):
    days: int
    totals: AnalyticsTotalsResponse
    timeseries: list[AnalyticsDayResponse]
    sources: list[AnalyticsSourceResponse]
    top_pages: list[AnalyticsPageResponse]
    top_articles: list[AnalyticsArticleResponse]
