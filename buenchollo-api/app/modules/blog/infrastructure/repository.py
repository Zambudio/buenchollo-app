from datetime import datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.modules.blog.domain.models import BlogPost, BlogCategory, BlogPostVote


class BlogCategoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_active(self) -> list[BlogCategory]:
        result = await self.session.execute(
            select(BlogCategory).where(BlogCategory.is_active.is_(True)).order_by(BlogCategory.sort_order, BlogCategory.name)
        )
        return list(result.scalars().all())

    async def get_all_admin(self) -> list[BlogCategory]:
        result = await self.session.execute(
            select(BlogCategory).order_by(BlogCategory.sort_order, BlogCategory.name)
        )
        return list(result.scalars().all())

    async def get_by_id(self, category_id: str) -> BlogCategory | None:
        result = await self.session.execute(select(BlogCategory).where(BlogCategory.id == category_id))
        return result.scalars().first()

    async def get_by_slug(self, slug: str) -> BlogCategory | None:
        result = await self.session.execute(select(BlogCategory).where(BlogCategory.slug == slug))
        return result.scalars().first()

    async def create(self, category: BlogCategory) -> BlogCategory:
        self.session.add(category)
        await self.session.flush()
        return category

    async def update(self, category: BlogCategory) -> BlogCategory:
        await self.session.flush()
        return category

    async def delete(self, category: BlogCategory) -> None:
        await self.session.delete(category)
        await self.session.flush()


class BlogPostRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _base_query():
        return select(BlogPost).options(selectinload(BlogPost.category))

    async def get_by_id(self, post_id: str) -> BlogPost | None:
        result = await self.session.execute(self._base_query().where(BlogPost.id == post_id))
        return result.scalars().first()

    async def get_by_slug(self, slug: str) -> BlogPost | None:
        """Cualquier estado — uso admin/preview."""
        result = await self.session.execute(self._base_query().where(BlogPost.slug == slug))
        return result.scalars().first()

    async def get_public_by_slug(self, slug: str) -> BlogPost | None:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            self._base_query().where(
                BlogPost.slug == slug,
                BlogPost.status == "published",
                BlogPost.published_at.is_not(None),
                BlogPost.published_at <= now,
            )
        )
        return result.scalars().first()

    async def slug_exists(self, slug: str, *, exclude_id: str | None = None) -> bool:
        query = select(BlogPost.id).where(BlogPost.slug == slug)
        if exclude_id:
            query = query.where(BlogPost.id != exclude_id)
        result = await self.session.execute(query)
        return result.scalar() is not None

    @staticmethod
    def _apply_public_filters(query, category_slug: str | None, search: str | None, featured_only: bool):
        now = datetime.now(timezone.utc)
        query = query.where(
            BlogPost.status == "published",
            BlogPost.published_at.is_not(None),
            BlogPost.published_at <= now,
        )
        if category_slug:
            query = query.join(BlogCategory, BlogPost.category_id == BlogCategory.id).where(BlogCategory.slug == category_slug)
        if search:
            like = f"%{search}%"
            query = query.where((BlogPost.title.ilike(like)) | (BlogPost.excerpt.ilike(like)))
        if featured_only:
            query = query.where(BlogPost.is_featured.is_(True))
        return query

    async def count_public(self, category_slug: str | None = None, search: str | None = None, featured_only: bool = False) -> int:
        query = self._apply_public_filters(select(func.count(BlogPost.id)), category_slug, search, featured_only)
        result = await self.session.execute(query)
        return int(result.scalar_one())

    async def list_public(
        self,
        category_slug: str | None = None,
        search: str | None = None,
        featured_only: bool = False,
        limit: int = 12,
        offset: int = 0,
    ) -> list[BlogPost]:
        query = self._apply_public_filters(self._base_query(), category_slug, search, featured_only)
        query = query.order_by(BlogPost.published_at.desc(), BlogPost.id.desc()).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_featured(self) -> BlogPost | None:
        posts = await self.list_public(featured_only=True, limit=1)
        return posts[0] if posts else None

    async def get_related(self, post: BlogPost, limit: int = 3) -> list[BlogPost]:
        if not post.category_id:
            return []
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            self._base_query()
            .where(
                BlogPost.category_id == post.category_id,
                BlogPost.id != post.id,
                BlogPost.status == "published",
                BlogPost.published_at.is_not(None),
                BlogPost.published_at <= now,
            )
            .order_by(BlogPost.published_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_admin(
        self,
        status: str | None = None,
        category_id: str | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[BlogPost], int]:
        base = self._base_query()
        count_base = select(func.count(BlogPost.id))
        if status and status != "all":
            base = base.where(BlogPost.status == status)
            count_base = count_base.where(BlogPost.status == status)
        if category_id:
            base = base.where(BlogPost.category_id == category_id)
            count_base = count_base.where(BlogPost.category_id == category_id)
        if search:
            like = f"%{search}%"
            base = base.where(BlogPost.title.ilike(like))
            count_base = count_base.where(BlogPost.title.ilike(like))

        total = int((await self.session.execute(count_base)).scalar_one())
        result = await self.session.execute(
            base.order_by(BlogPost.updated_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_due_scheduled(self) -> list[BlogPost]:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(BlogPost).where(BlogPost.status == "scheduled", BlogPost.scheduled_for <= now)
        )
        return list(result.scalars().all())

    async def get_sitemap_entries(self) -> list[BlogPost]:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(BlogPost)
            .where(BlogPost.status == "published", BlogPost.published_at.is_not(None), BlogPost.published_at <= now)
            .order_by(BlogPost.published_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, post: BlogPost) -> BlogPost:
        self.session.add(post)
        await self.session.flush()
        return post

    async def update(self, post: BlogPost) -> BlogPost:
        await self.session.flush()
        return post

    async def delete(self, post: BlogPost) -> None:
        await self.session.delete(post)
        await self.session.flush()

    # --- Votos ("¿te ha sido útil?") ---

    async def get_user_vote(self, blog_post_id: str, user_id: str) -> int | None:
        result = await self.session.execute(
            select(BlogPostVote.vote).where(
                BlogPostVote.blog_post_id == blog_post_id, BlogPostVote.user_id == user_id
            )
        )
        return result.scalar()

    async def upsert_vote(self, blog_post_id: str, user_id: str, vote: int) -> None:
        stmt = pg_insert(BlogPostVote).values(
            blog_post_id=blog_post_id, user_id=user_id, vote=vote
        ).on_conflict_do_update(
            index_elements=["blog_post_id", "user_id"],
            set_={"vote": vote},
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def delete_vote(self, blog_post_id: str, user_id: str) -> None:
        result = await self.session.execute(
            select(BlogPostVote).where(
                BlogPostVote.blog_post_id == blog_post_id, BlogPostVote.user_id == user_id
            )
        )
        vote_obj = result.scalars().first()
        if vote_obj:
            await self.session.delete(vote_obj)
            await self.session.flush()

    async def recalculate_votes(self, blog_post_id: str) -> dict:
        """Recalcula votes_up/votes_down desde blog_post_votes y actualiza el post."""
        row = (await self.session.execute(
            text("""
                UPDATE blog_posts SET
                    votes_up   = (SELECT COUNT(*) FROM blog_post_votes WHERE blog_post_id = CAST(:id AS uuid) AND vote = 1),
                    votes_down = (SELECT COUNT(*) FROM blog_post_votes WHERE blog_post_id = CAST(:id AS uuid) AND vote = -1)
                WHERE id = CAST(:id AS uuid)
                RETURNING votes_up, votes_down
            """),
            {"id": blog_post_id},
        )).mappings().first()
        return dict(row) if row else {"votes_up": 0, "votes_down": 0}

    async def get_authors(self, user_ids: list[str]) -> dict[str, str | None]:
        """Nombre a mostrar de varios autores en una sola query (evita N+1
        en el listado admin y en el detalle público)."""
        ids = [uid for uid in set(user_ids) if uid]
        if not ids:
            return {}
        result = await self.session.execute(
            text("SELECT user_id, display_name FROM profiles WHERE user_id::text = ANY(:ids)"),
            {"ids": ids},
        )
        return {str(row.user_id): row.display_name for row in result}
