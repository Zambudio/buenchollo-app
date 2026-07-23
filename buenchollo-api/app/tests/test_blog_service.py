import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.modules.blog.application.blog_service import BlogPostService
from app.modules.blog.domain.exceptions import BlogPostNotFound, DuplicateSlugError, PostNotPublishableError
from app.modules.blog.domain.models import BlogCategory, BlogPost
from app.modules.blog.domain.ports import DealSummary

pytestmark = pytest.mark.asyncio

VALID_DOC = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Hola mundo"}]}]}


class FakePostRepo:
    def __init__(self):
        self.posts: dict[str, BlogPost] = {}
        self.votes: dict[tuple[str, str], int] = {}

    async def slug_exists(self, slug, exclude_id=None):
        return any(p.slug == slug and p.id != exclude_id for p in self.posts.values())

    async def create(self, post: BlogPost) -> BlogPost:
        post.id = post.id or str(uuid.uuid4())
        self.posts[post.id] = post
        return post

    async def get_by_id(self, post_id):
        return self.posts.get(post_id)

    async def update(self, post: BlogPost) -> BlogPost:
        self.posts[post.id] = post
        return post

    async def delete(self, post: BlogPost) -> None:
        self.posts.pop(post.id, None)

    async def get_user_vote(self, post_id: str, user_id: str) -> int | None:
        return self.votes.get((post_id, user_id))

    async def upsert_vote(self, post_id: str, user_id: str, vote: int) -> None:
        self.votes[(post_id, user_id)] = vote

    async def delete_vote(self, post_id: str, user_id: str) -> None:
        self.votes.pop((post_id, user_id), None)

    async def recalculate_votes(self, post_id: str) -> dict:
        votes = [v for (pid, _), v in self.votes.items() if pid == post_id]
        counters = {"votes_up": sum(1 for v in votes if v == 1), "votes_down": sum(1 for v in votes if v == -1)}
        post = self.posts.get(post_id)
        if post:
            post.votes_up, post.votes_down = counters["votes_up"], counters["votes_down"]
        return counters


class FakeCategoryRepo:
    def __init__(self, categories: dict[str, BlogCategory] | None = None):
        self.categories = categories or {}

    async def get_by_id(self, category_id):
        return self.categories.get(category_id)


class FakeDealLookup:
    def __init__(self, summaries: dict[str, DealSummary] | None = None):
        self.summaries = summaries or {}
        self.calls: list[list[str]] = []

    async def get_many(self, deal_ids: list[str]) -> dict[str, DealSummary]:
        self.calls.append(deal_ids)
        return {i: self.summaries[i] for i in deal_ids if i in self.summaries}


def _publishable_fields(**overrides) -> dict:
    fields = dict(
        title="Un artículo de prueba",
        excerpt="Resumen",
        content=VALID_DOC,
        cover_image_url="https://cdn.example.com/cover.png",
        cover_image_alt="Portada",
    )
    fields.update(overrides)
    return fields


@pytest.fixture
def active_category():
    return BlogCategory(id="cat-1", name="Auriculares", slug="auriculares", is_active=True)


@pytest.fixture
def service(active_category):
    post_repo = FakePostRepo()
    category_repo = FakeCategoryRepo({active_category.id: active_category})
    return BlogPostService(post_repo, category_repo, FakeDealLookup())


async def test_create_post_genera_slug_desde_el_titulo(service):
    post = await service.create_post({"title": "Los Mejores Auriculares 2026"}, author_id="user-1")
    assert post.slug == "los-mejores-auriculares-2026"
    assert post.status == "draft"
    assert post.author_id == "user-1"


async def test_create_post_slug_duplicado_lanza(service):
    await service.create_post({"title": "Título", "slug": "mi-slug"}, author_id="user-1")
    with pytest.raises(DuplicateSlugError):
        await service.create_post({"title": "Otro", "slug": "mi-slug"}, author_id="user-1")


async def test_update_post_no_regenera_slug_al_cambiar_titulo(service):
    post = await service.create_post({"title": "Título original", "slug": "titulo-original"}, author_id="u1")
    updated = await service.update_post(post.id, {"title": "Título cambiado"})
    assert updated.slug == "titulo-original"
    assert updated.title == "Título cambiado"


async def test_publish_falla_si_faltan_campos_obligatorios(service):
    post = await service.create_post({"title": "Incompleto"}, author_id="u1")
    with pytest.raises(PostNotPublishableError) as exc:
        await service.publish_post(post.id)
    assert "excerpt" in exc.value.payload["missing_fields"]
    assert "cover_image_url" in exc.value.payload["missing_fields"]
    assert "category_id" in exc.value.payload["missing_fields"]


async def test_publish_ok_marca_published_at_y_limpia_scheduled_for(service, active_category):
    post = await service.create_post(
        _publishable_fields(title="Completo", category_id=active_category.id), author_id="u1",
    )
    published = await service.publish_post(post.id)
    assert published.status == "published"
    assert published.published_at is not None
    assert published.scheduled_for is None


async def test_publish_post_inexistente_lanza_not_found(service):
    with pytest.raises(BlogPostNotFound):
        await service.publish_post("no-existe")


async def test_schedule_requiere_fecha_futura(service, active_category):
    post = await service.create_post(
        _publishable_fields(title="Programable", category_id=active_category.id), author_id="u1",
    )
    past = datetime.now(timezone.utc) - timedelta(days=1)
    with pytest.raises(PostNotPublishableError) as exc:
        await service.schedule_post(post.id, past)
    assert "scheduled_for" in exc.value.payload["missing_fields"]


async def test_schedule_ok_deja_published_at_vacio(service, active_category):
    post = await service.create_post(
        _publishable_fields(title="Programable", category_id=active_category.id), author_id="u1",
    )
    future = datetime.now(timezone.utc) + timedelta(days=1)
    scheduled = await service.schedule_post(post.id, future)
    assert scheduled.status == "scheduled"
    assert scheduled.scheduled_for == future
    assert scheduled.published_at is None


async def test_archive_cambia_status(service, active_category):
    post = await service.create_post(
        _publishable_fields(title="A archivar", category_id=active_category.id), author_id="u1",
    )
    await service.publish_post(post.id)
    archived = await service.archive_post(post.id)
    assert archived.status == "archived"


async def test_resolve_products_resuelve_en_lote():
    doc = {
        "type": "doc",
        "content": [
            {"type": "productRecommendation", "attrs": {"mode": "deal", "deal_id": "d1"}},
            {"type": "productRecommendation", "attrs": {"mode": "deal", "deal_id": "d2"}},
        ],
    }
    summary = DealSummary(
        id="d1", title="Auriculares X", slug="auriculares-x", image_url=None,
        affiliate_url="https://amazon.es/dp/x", store_name="Amazon",
        current_price=19.99, previous_price=29.99, discount_percentage=33, is_active=True,
    )
    lookup = FakeDealLookup({"d1": summary})
    post_repo = FakePostRepo()
    service = BlogPostService(post_repo, FakeCategoryRepo(), lookup)
    post = BlogPost(id="p1", title="t", slug="t", content=doc)

    resolved = await service.resolve_products(post)

    assert lookup.calls == [["d1", "d2"]]
    assert set(resolved.keys()) == {"d1"}


async def test_process_vote_registra_voto_y_actualiza_contadores(service, active_category):
    post = await service.create_post(
        _publishable_fields(title="Votable", category_id=active_category.id), author_id="u1",
    )
    result = await service.process_vote(post.id, "voter-1", 1)
    assert result == {"votes_up": 1, "votes_down": 0, "my_vote": 1}


async def test_process_vote_repetir_el_mismo_voto_lo_retira(service, active_category):
    post = await service.create_post(
        _publishable_fields(title="Votable", category_id=active_category.id), author_id="u1",
    )
    await service.process_vote(post.id, "voter-1", 1)
    result = await service.process_vote(post.id, "voter-1", 1)
    assert result == {"votes_up": 0, "votes_down": 0, "my_vote": 0}


async def test_process_vote_cambiar_de_voto_actualiza_ambos_contadores(service, active_category):
    post = await service.create_post(
        _publishable_fields(title="Votable", category_id=active_category.id), author_id="u1",
    )
    await service.process_vote(post.id, "voter-1", 1)
    result = await service.process_vote(post.id, "voter-1", -1)
    assert result == {"votes_up": 0, "votes_down": 1, "my_vote": -1}
