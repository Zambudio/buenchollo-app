import logging
from datetime import datetime, timezone

from app.modules.blog.domain.affiliate_domains import get_allowed_affiliate_domains
from app.modules.blog.domain.content import (
    extract_referenced_deal_ids,
    has_affiliate_blocks,
    is_content_empty,
    validate_document,
)
from app.modules.blog.domain.exceptions import BlogPostNotFound, DuplicateSlugError, PostNotPublishableError
from app.modules.blog.domain.models import BlogPost
from app.modules.blog.domain.ports import DealLookupPort, DealSummary
from app.modules.blog.domain.utils import normalize_tags, slugify
from app.modules.blog.infrastructure.repository import BlogCategoryRepository, BlogPostRepository

logger = logging.getLogger(__name__)

_DEFAULT_DOC = {"type": "doc", "content": []}


class BlogPostService:
    def __init__(
        self,
        repo: BlogPostRepository,
        category_repo: BlogCategoryRepository,
        deal_lookup: DealLookupPort | None = None,
    ):
        self.repo = repo
        self.category_repo = category_repo
        self.deal_lookup = deal_lookup

    async def _ensure_unique_slug(self, slug: str, *, exclude_id: str | None = None) -> None:
        if await self.repo.slug_exists(slug, exclude_id=exclude_id):
            raise DuplicateSlugError(slug)

    def _validate_content_if_present(self, data: dict) -> None:
        if "content" in data and data["content"] is not None:
            validate_document(data["content"], allowed_affiliate_domains=get_allowed_affiliate_domains())

    async def create_post(self, data: dict, author_id: str) -> BlogPost:
        data = dict(data)
        data["tags"] = normalize_tags(data.get("tags"))
        if not data.get("slug"):
            data["slug"] = slugify(data["title"])
        await self._ensure_unique_slug(data["slug"])
        data.setdefault("content", dict(_DEFAULT_DOC))
        data.setdefault("status", "draft")
        self._validate_content_if_present(data)
        data["author_id"] = author_id
        post = BlogPost(**data)
        created = await self.repo.create(post)
        return await self.repo.get_by_id(created.id)

    async def update_post(self, post_id: str, data: dict) -> BlogPost | None:
        post = await self.repo.get_by_id(post_id)
        if not post:
            return None
        data = dict(data)
        if "tags" in data:
            data["tags"] = normalize_tags(data["tags"])
        if "slug" in data and data["slug"] and data["slug"] != post.slug:
            await self._ensure_unique_slug(data["slug"], exclude_id=post_id)
        self._validate_content_if_present(data)
        for field, value in data.items():
            setattr(post, field, value)
        await self.repo.update(post)
        return await self.repo.get_by_id(post_id)

    async def delete_post(self, post_id: str) -> bool:
        post = await self.repo.get_by_id(post_id)
        if not post:
            return False
        await self.repo.delete(post)
        return True

    async def _publishability_errors(self, post: BlogPost) -> list[str]:
        missing: list[str] = []
        if not post.title or not post.title.strip():
            missing.append("title")
        if not post.slug:
            missing.append("slug")
        if not post.excerpt or not post.excerpt.strip():
            missing.append("excerpt")
        if is_content_empty(post.content or {}):
            missing.append("content")
        if not post.cover_image_url:
            missing.append("cover_image_url")
        if not post.cover_image_alt:
            missing.append("cover_image_alt")
        if not post.author_id:
            missing.append("author_id")
        if not post.category_id:
            missing.append("category_id")
        else:
            category = await self.category_repo.get_by_id(post.category_id)
            if not category or not category.is_active:
                missing.append("category_id")
        try:
            validate_document(post.content or {}, allowed_affiliate_domains=get_allowed_affiliate_domains())
        except Exception:
            missing.append("content")
        return missing

    async def publish_post(self, post_id: str) -> BlogPost:
        post = await self.repo.get_by_id(post_id)
        if not post:
            raise BlogPostNotFound(post_id)
        missing = await self._publishability_errors(post)
        if missing:
            raise PostNotPublishableError(missing)
        post.status = "published"
        if post.published_at is None:
            post.published_at = datetime.now(timezone.utc)
        post.scheduled_for = None
        await self.repo.update(post)
        return await self.repo.get_by_id(post_id)

    async def schedule_post(self, post_id: str, scheduled_for: datetime) -> BlogPost:
        post = await self.repo.get_by_id(post_id)
        if not post:
            raise BlogPostNotFound(post_id)
        now = datetime.now(timezone.utc)
        if scheduled_for.tzinfo is None:
            scheduled_for = scheduled_for.replace(tzinfo=timezone.utc)
        missing = await self._publishability_errors(post)
        if scheduled_for <= now:
            missing.append("scheduled_for")
        if missing:
            raise PostNotPublishableError(missing)
        post.status = "scheduled"
        post.scheduled_for = scheduled_for
        await self.repo.update(post)
        return await self.repo.get_by_id(post_id)

    async def archive_post(self, post_id: str) -> BlogPost:
        post = await self.repo.get_by_id(post_id)
        if not post:
            raise BlogPostNotFound(post_id)
        post.status = "archived"
        await self.repo.update(post)
        return await self.repo.get_by_id(post_id)

    async def process_vote(self, post_id: str, user_id: str, vote: int) -> dict:
        """Aplica el voto de utilidad (toggle si es el mismo) y devuelve los contadores actualizados."""
        current_vote = await self.repo.get_user_vote(post_id, user_id)

        if current_vote == vote:
            await self.repo.delete_vote(post_id, user_id)
            my_vote = 0
        else:
            await self.repo.upsert_vote(post_id, user_id, vote)
            my_vote = vote

        counters = await self.repo.recalculate_votes(post_id)
        return {**counters, "my_vote": my_vote}

    async def resolve_products(self, post: BlogPost) -> dict[str, DealSummary]:
        if not self.deal_lookup:
            return {}
        deal_ids = extract_referenced_deal_ids(post.content or {})
        return await self.deal_lookup.get_many(deal_ids)

    @staticmethod
    def has_affiliate_disclosure(post: BlogPost) -> bool:
        return has_affiliate_blocks(post.content or {})
