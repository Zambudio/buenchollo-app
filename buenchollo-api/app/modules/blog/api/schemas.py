from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

_TITLE_MAX = 180
_EXCERPT_MAX = 500
_SLUG_MAX = 200
_SEO_TITLE_MAX = 200
_SEO_DESC_MAX = 320
_URL_MAX = 2048
_CATEGORY_NAME_MAX = 100
_CATEGORY_DESC_MAX = 500

STATUSES = Literal["draft", "scheduled", "published", "archived"]


# ── Categorías ────────────────────────────────────────────────────────────

class BlogCategoryResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None
    is_active: bool
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class BlogCategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=_CATEGORY_NAME_MAX)
    slug: str = Field(min_length=2, max_length=_SLUG_MAX)
    description: str | None = Field(default=None, max_length=_CATEGORY_DESC_MAX)
    is_active: bool = True
    sort_order: int = 0


class BlogCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=_CATEGORY_NAME_MAX)
    slug: str | None = Field(default=None, min_length=2, max_length=_SLUG_MAX)
    description: str | None = Field(default=None, max_length=_CATEGORY_DESC_MAX)
    is_active: bool | None = None
    sort_order: int | None = None


# ── Artículos: piezas comunes ────────────────────────────────────────────

class AuthorBasic(BaseModel):
    id: str
    display_name: str | None = None


class DealSummaryResponse(BaseModel):
    id: str
    title: str
    slug: str
    image_url: str | None = None
    affiliate_url: str
    store_name: str | None = None
    current_price: float | None = None
    previous_price: float | None = None
    discount_percentage: int | None = None
    is_active: bool


class TocEntryResponse(BaseModel):
    level: int
    text: str
    id: str


# ── Artículos: público ───────────────────────────────────────────────────

class BlogPostCardResponse(BaseModel):
    id: str
    title: str
    slug: str
    excerpt: str | None = None
    cover_image_url: str | None = None
    cover_image_alt: str | None = None
    tags: list[str] = []
    is_featured: bool
    published_at: datetime | None = None
    reading_time_minutes: int
    category: BlogCategoryResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class BlogPostPageResponse(BaseModel):
    items: list[BlogPostCardResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


class BlogPostDetailResponse(BaseModel):
    id: str
    title: str
    slug: str
    excerpt: str | None = None
    content: dict[str, Any]
    cover_image_url: str | None = None
    cover_image_alt: str | None = None
    tags: list[str] = []
    is_featured: bool
    status: STATUSES
    published_at: datetime | None = None
    updated_at: datetime
    category: BlogCategoryResponse | None = None
    author: AuthorBasic | None = None

    seo_title: str | None = None
    seo_description: str | None = None
    canonical_url: str | None = None
    og_image_url: str | None = None

    reading_time_minutes: int
    word_count: int
    toc: list[TocEntryResponse] = []
    has_affiliate_links: bool
    products: dict[str, DealSummaryResponse] = {}

    votes_up: int = 0
    votes_down: int = 0

    model_config = ConfigDict(from_attributes=True)


class PostVoteRequest(BaseModel):
    vote: Literal[-1, 1]


class PostVoteResponse(BaseModel):
    votes_up: int
    votes_down: int
    my_vote: int


# ── Artículos: admin ─────────────────────────────────────────────────────

class BlogPostAdminListItem(BaseModel):
    id: str
    title: str
    slug: str
    status: STATUSES
    cover_image_url: str | None = None
    is_featured: bool
    updated_at: datetime
    published_at: datetime | None = None
    scheduled_for: datetime | None = None
    category: BlogCategoryResponse | None = None
    author: AuthorBasic | None = None

    model_config = ConfigDict(from_attributes=True)


class BlogPostAdminPageResponse(BaseModel):
    items: list[BlogPostAdminListItem]
    page: int
    page_size: int
    total: int
    total_pages: int


class BlogPostCreate(BaseModel):
    title: str = Field(min_length=3, max_length=_TITLE_MAX)
    slug: str | None = Field(default=None, max_length=_SLUG_MAX)
    excerpt: str | None = Field(default=None, max_length=_EXCERPT_MAX)
    content: dict[str, Any] | None = None
    cover_image_url: str | None = Field(default=None, max_length=_URL_MAX)
    cover_image_alt: str | None = Field(default=None, max_length=300)
    category_id: str | None = None
    tags: list[str] = Field(default_factory=list, max_length=20)
    seo_title: str | None = Field(default=None, max_length=_SEO_TITLE_MAX)
    seo_description: str | None = Field(default=None, max_length=_SEO_DESC_MAX)
    canonical_url: str | None = Field(default=None, max_length=_URL_MAX)
    og_image_url: str | None = Field(default=None, max_length=_URL_MAX)
    is_featured: bool = False


class BlogPostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=_TITLE_MAX)
    slug: str | None = Field(default=None, max_length=_SLUG_MAX)
    excerpt: str | None = Field(default=None, max_length=_EXCERPT_MAX)
    content: dict[str, Any] | None = None
    cover_image_url: str | None = Field(default=None, max_length=_URL_MAX)
    cover_image_alt: str | None = Field(default=None, max_length=300)
    category_id: str | None = None
    tags: list[str] | None = Field(default=None, max_length=20)
    seo_title: str | None = Field(default=None, max_length=_SEO_TITLE_MAX)
    seo_description: str | None = Field(default=None, max_length=_SEO_DESC_MAX)
    canonical_url: str | None = Field(default=None, max_length=_URL_MAX)
    og_image_url: str | None = Field(default=None, max_length=_URL_MAX)
    is_featured: bool | None = None


class SchedulePostRequest(BaseModel):
    scheduled_for: datetime


class SitemapEntryResponse(BaseModel):
    slug: str
    updated_at: datetime
    published_at: datetime | None = None
