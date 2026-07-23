import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_log
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import get_current_user, require_admin
from app.modules.blog.api.schemas import (
    BlogCategoryCreate,
    BlogCategoryResponse,
    BlogCategoryUpdate,
    BlogPostAdminListItem,
    BlogPostAdminPageResponse,
    BlogPostCardResponse,
    BlogPostCreate,
    BlogPostDetailResponse,
    BlogPostPageResponse,
    BlogPostUpdate,
    PostVoteRequest,
    PostVoteResponse,
    SchedulePostRequest,
    SitemapEntryResponse,
)
from app.modules.blog.application.blog_service import BlogPostService
from app.modules.blog.domain.content import count_words, extract_plain_text, extract_toc, reading_time_minutes
from app.modules.blog.domain.exceptions import BlogCategoryNotFound, BlogPostNotFound
from app.modules.blog.domain.models import BlogPost
from app.modules.blog.infrastructure.deal_lookup_adapter import DealLookupAdapter
from app.modules.blog.infrastructure.repository import BlogCategoryRepository, BlogPostRepository
from app.modules.deals.infrastructure.repository import DealRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/blog", tags=["blog"])


def get_post_repository(db: AsyncSession = Depends(get_db)) -> BlogPostRepository:
    return BlogPostRepository(db)


def get_category_repository(db: AsyncSession = Depends(get_db)) -> BlogCategoryRepository:
    return BlogCategoryRepository(db)


def get_post_service(db: AsyncSession = Depends(get_db)) -> BlogPostService:
    repo = BlogPostRepository(db)
    category_repo = BlogCategoryRepository(db)
    deal_lookup = DealLookupAdapter(DealRepository(db))
    return BlogPostService(repo, category_repo, deal_lookup)


# ── Helpers de serialización (cálculos derivados del documento Tiptap) ─────

def _card_response(post: BlogPost) -> BlogPostCardResponse:
    text = extract_plain_text(post.content or {})
    words = count_words(text)
    return BlogPostCardResponse(
        id=post.id,
        title=post.title,
        slug=post.slug,
        excerpt=post.excerpt,
        cover_image_url=post.cover_image_url,
        cover_image_alt=post.cover_image_alt,
        tags=post.tags or [],
        is_featured=post.is_featured,
        published_at=post.published_at,
        reading_time_minutes=reading_time_minutes(words),
        category=BlogCategoryResponse.model_validate(post.category) if post.category else None,
    )


def _admin_list_item(post: BlogPost, authors: dict[str, str | None]) -> BlogPostAdminListItem:
    return BlogPostAdminListItem(
        id=post.id,
        title=post.title,
        slug=post.slug,
        status=post.status,
        cover_image_url=post.cover_image_url,
        is_featured=post.is_featured,
        updated_at=post.updated_at,
        published_at=post.published_at,
        scheduled_for=post.scheduled_for,
        category=BlogCategoryResponse.model_validate(post.category) if post.category else None,
        author={"id": post.author_id, "display_name": authors.get(post.author_id)} if post.author_id else None,
    )


async def _detail_response(post: BlogPost, service: BlogPostService, repo: BlogPostRepository) -> BlogPostDetailResponse:
    text = extract_plain_text(post.content or {})
    words = count_words(text)
    toc = extract_toc(post.content or {})
    products = await service.resolve_products(post)
    authors = await repo.get_authors([post.author_id] if post.author_id else [])
    return BlogPostDetailResponse(
        id=post.id,
        title=post.title,
        slug=post.slug,
        excerpt=post.excerpt,
        content=post.content or {},
        cover_image_url=post.cover_image_url,
        cover_image_alt=post.cover_image_alt,
        tags=post.tags or [],
        is_featured=post.is_featured,
        status=post.status,
        published_at=post.published_at,
        updated_at=post.updated_at,
        category=BlogCategoryResponse.model_validate(post.category) if post.category else None,
        author={"id": post.author_id, "display_name": authors.get(post.author_id)} if post.author_id else None,
        seo_title=post.seo_title,
        seo_description=post.seo_description,
        canonical_url=post.canonical_url,
        og_image_url=post.og_image_url,
        reading_time_minutes=reading_time_minutes(words),
        word_count=words,
        toc=[t.__dict__ for t in toc],
        has_affiliate_links=service.has_affiliate_disclosure(post),
        products={k: v.__dict__ for k, v in products.items()},
        votes_up=post.votes_up,
        votes_down=post.votes_down,
    )


# ── Endpoints públicos ──────────────────────────────────────────────────────

@router.get("/categories", response_model=list[BlogCategoryResponse])
async def list_public_categories(repo: BlogCategoryRepository = Depends(get_category_repository)):
    return await repo.get_all_active()


@router.get("/sitemap", response_model=list[SitemapEntryResponse])
async def get_sitemap_entries(repo: BlogPostRepository = Depends(get_post_repository)):
    posts = await repo.get_sitemap_entries()
    return [
        SitemapEntryResponse(slug=p.slug, updated_at=p.updated_at, published_at=p.published_at)
        for p in posts
    ]


@router.get("/posts", response_model=BlogPostPageResponse)
@limiter.limit("60/minute")
async def list_public_posts(
    request: Request,
    category: str | None = Query(default=None, description="Slug de categoría"),
    search: str | None = Query(default=None, max_length=200),
    featured: bool = Query(default=False),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=48),
    repo: BlogPostRepository = Depends(get_post_repository),
):
    total = await repo.count_public(category_slug=category, search=search, featured_only=featured)
    total_pages = max(1, (total + page_size - 1) // page_size)
    current_page = min(page, total_pages)
    items = await repo.list_public(
        category_slug=category, search=search, featured_only=featured,
        limit=page_size, offset=(current_page - 1) * page_size,
    )
    return BlogPostPageResponse(
        items=[_card_response(p) for p in items],
        page=current_page, page_size=page_size, total=total, total_pages=total_pages,
    )


@router.get("/posts/{slug}", response_model=BlogPostDetailResponse)
async def get_public_post_by_slug(
    slug: str,
    repo: BlogPostRepository = Depends(get_post_repository),
    service: BlogPostService = Depends(get_post_service),
):
    post = await repo.get_public_by_slug(slug)
    if not post:
        raise BlogPostNotFound(slug)
    return await _detail_response(post, service, repo)


@router.post("/posts/{post_id}/vote", response_model=PostVoteResponse)
@limiter.limit("30/minute")  # anti-spam de votos
async def vote_on_post(
    request: Request,
    post_id: str,
    vote_in: PostVoteRequest,
    repo: BlogPostRepository = Depends(get_post_repository),
    service: BlogPostService = Depends(get_post_service),
    current_user=Depends(get_current_user),
):
    post = await repo.get_by_id(post_id)
    if not post:
        raise BlogPostNotFound(post_id)
    result = await service.process_vote(post_id, str(current_user.id), vote_in.vote)
    return PostVoteResponse(**result)


@router.get("/posts/{post_id}/my-vote")
async def get_my_vote(
    post_id: str,
    repo: BlogPostRepository = Depends(get_post_repository),
    current_user=Depends(get_current_user),
) -> dict:
    my_vote = await repo.get_user_vote(post_id, str(current_user.id))
    return {"my_vote": my_vote or 0}


@router.get("/posts/{slug}/related", response_model=list[BlogPostCardResponse])
async def get_related_posts(
    slug: str,
    limit: int = Query(3, ge=1, le=6),
    repo: BlogPostRepository = Depends(get_post_repository),
):
    post = await repo.get_public_by_slug(slug)
    if not post:
        raise BlogPostNotFound(slug)
    related = await repo.get_related(post, limit=limit)
    return [_card_response(p) for p in related]


# ── Endpoints admin: categorías ──────────────────────────────────────────────

@router.get("/admin/categories", response_model=list[BlogCategoryResponse])
async def list_admin_categories(
    repo: BlogCategoryRepository = Depends(get_category_repository),
    _current_user=Depends(require_admin),
):
    return await repo.get_all_admin()


@router.post("/admin/categories", response_model=BlogCategoryResponse)
async def create_category(
    category_in: BlogCategoryCreate,
    db: AsyncSession = Depends(get_db),
    repo: BlogCategoryRepository = Depends(get_category_repository),
    current_user=Depends(require_admin),
):
    from app.modules.blog.domain.models import BlogCategory
    created = await repo.create(BlogCategory(**category_in.model_dump()))
    await audit_log(
        db, user_id=str(current_user.id), action="blog.category.create",
        target_type="blog_category", target_id=str(created.id),
        payload={"name": created.name, "slug": created.slug},
    )
    return created


@router.put("/admin/categories/{category_id}", response_model=BlogCategoryResponse)
async def update_category(
    category_id: str,
    category_in: BlogCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    repo: BlogCategoryRepository = Depends(get_category_repository),
    current_user=Depends(require_admin),
):
    category = await repo.get_by_id(category_id)
    if not category:
        raise BlogCategoryNotFound(category_id)
    diff = category_in.model_dump(exclude_unset=True)
    for field, value in diff.items():
        setattr(category, field, value)
    await repo.update(category)
    await audit_log(
        db, user_id=str(current_user.id), action="blog.category.update",
        target_type="blog_category", target_id=category_id,
        payload={"changed_fields": list(diff.keys())},
    )
    return category


@router.delete("/admin/categories/{category_id}", status_code=204)
async def delete_category(
    category_id: str,
    db: AsyncSession = Depends(get_db),
    repo: BlogCategoryRepository = Depends(get_category_repository),
    current_user=Depends(require_admin),
):
    category = await repo.get_by_id(category_id)
    if not category:
        raise BlogCategoryNotFound(category_id)
    await repo.delete(category)
    await audit_log(
        db, user_id=str(current_user.id), action="blog.category.delete",
        target_type="blog_category", target_id=category_id,
        payload={"name": category.name, "slug": category.slug},
    )


# ── Endpoints admin: artículos ───────────────────────────────────────────────

@router.get("/admin/posts", response_model=BlogPostAdminPageResponse)
async def list_admin_posts(
    status: str | None = None,
    category_id: str | None = None,
    search: str | None = Query(default=None, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    repo: BlogPostRepository = Depends(get_post_repository),
    _current_user=Depends(require_admin),
):
    offset = (page - 1) * page_size
    items, total = await repo.list_admin(status=status, category_id=category_id, search=search, limit=page_size, offset=offset)
    authors = await repo.get_authors([p.author_id for p in items if p.author_id])
    total_pages = max(1, (total + page_size - 1) // page_size)
    return BlogPostAdminPageResponse(
        items=[_admin_list_item(p, authors) for p in items],
        page=page, page_size=page_size, total=total, total_pages=total_pages,
    )


@router.get("/admin/posts/{post_id}", response_model=BlogPostDetailResponse)
async def get_admin_post(
    post_id: str,
    repo: BlogPostRepository = Depends(get_post_repository),
    service: BlogPostService = Depends(get_post_service),
    _current_user=Depends(require_admin),
):
    post = await repo.get_by_id(post_id)
    if not post:
        raise BlogPostNotFound(post_id)
    return await _detail_response(post, service, repo)


@router.post("/admin/posts", response_model=BlogPostDetailResponse)
async def create_post(
    post_in: BlogPostCreate,
    db: AsyncSession = Depends(get_db),
    service: BlogPostService = Depends(get_post_service),
    repo: BlogPostRepository = Depends(get_post_repository),
    current_user=Depends(require_admin),
):
    payload = post_in.model_dump(exclude_none=True)
    created = await service.create_post(payload, str(current_user.id))
    await audit_log(
        db, user_id=str(current_user.id), action="blog.post.create",
        target_type="blog_post", target_id=str(created.id),
        payload={"title": created.title, "slug": created.slug, "status": created.status},
    )
    return await _detail_response(created, service, repo)


@router.put("/admin/posts/{post_id}", response_model=BlogPostDetailResponse)
async def update_post(
    post_id: str,
    post_in: BlogPostUpdate,
    db: AsyncSession = Depends(get_db),
    service: BlogPostService = Depends(get_post_service),
    repo: BlogPostRepository = Depends(get_post_repository),
    current_user=Depends(require_admin),
):
    diff = post_in.model_dump(exclude_unset=True)
    updated = await service.update_post(post_id, diff)
    if not updated:
        raise BlogPostNotFound(post_id)
    await audit_log(
        db, user_id=str(current_user.id), action="blog.post.update",
        target_type="blog_post", target_id=post_id,
        payload={"changed_fields": [f for f in diff.keys() if f != "content"]},
    )
    return await _detail_response(updated, service, repo)


@router.delete("/admin/posts/{post_id}", status_code=204)
async def delete_post(
    post_id: str,
    db: AsyncSession = Depends(get_db),
    service: BlogPostService = Depends(get_post_service),
    repo: BlogPostRepository = Depends(get_post_repository),
    current_user=Depends(require_admin),
):
    post = await repo.get_by_id(post_id)
    if not post:
        raise BlogPostNotFound(post_id)
    await service.delete_post(post_id)
    await audit_log(
        db, user_id=str(current_user.id), action="blog.post.delete",
        target_type="blog_post", target_id=post_id,
        payload={"title": post.title, "slug": post.slug},
    )


@router.post("/admin/posts/{post_id}/publish", response_model=BlogPostDetailResponse)
async def publish_post(
    post_id: str,
    db: AsyncSession = Depends(get_db),
    service: BlogPostService = Depends(get_post_service),
    repo: BlogPostRepository = Depends(get_post_repository),
    current_user=Depends(require_admin),
):
    published = await service.publish_post(post_id)
    await audit_log(
        db, user_id=str(current_user.id), action="blog.post.publish",
        target_type="blog_post", target_id=post_id,
        payload={"slug": published.slug},
    )
    return await _detail_response(published, service, repo)


@router.post("/admin/posts/{post_id}/schedule", response_model=BlogPostDetailResponse)
async def schedule_post(
    post_id: str,
    schedule_in: SchedulePostRequest,
    db: AsyncSession = Depends(get_db),
    service: BlogPostService = Depends(get_post_service),
    repo: BlogPostRepository = Depends(get_post_repository),
    current_user=Depends(require_admin),
):
    scheduled = await service.schedule_post(post_id, schedule_in.scheduled_for)
    await audit_log(
        db, user_id=str(current_user.id), action="blog.post.schedule",
        target_type="blog_post", target_id=post_id,
        payload={"slug": scheduled.slug, "scheduled_for": scheduled.scheduled_for.isoformat() if scheduled.scheduled_for else None},
    )
    return await _detail_response(scheduled, service, repo)


@router.post("/admin/posts/{post_id}/archive", response_model=BlogPostDetailResponse)
async def archive_post(
    post_id: str,
    db: AsyncSession = Depends(get_db),
    service: BlogPostService = Depends(get_post_service),
    repo: BlogPostRepository = Depends(get_post_repository),
    current_user=Depends(require_admin),
):
    archived = await service.archive_post(post_id)
    await audit_log(
        db, user_id=str(current_user.id), action="blog.post.archive",
        target_type="blog_post", target_id=post_id,
        payload={"slug": archived.slug},
    )
    return await _detail_response(archived, service, repo)
