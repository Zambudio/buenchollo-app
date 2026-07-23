from datetime import datetime, timedelta, timezone

import pytest

from app.modules.blog.application.scheduler import _publish_due_posts
from app.modules.blog.domain.models import BlogPost

pytestmark = pytest.mark.asyncio


class FakeRepo:
    def __init__(self, due: list[BlogPost]):
        self._due = due
        self.updated: list[BlogPost] = []

    async def get_due_scheduled(self):
        return self._due

    async def update(self, post):
        self.updated.append(post)
        return post


def _scheduled_post(post_id: str) -> BlogPost:
    return BlogPost(
        id=post_id, title="t", slug=f"slug-{post_id}",
        status="scheduled",
        scheduled_for=datetime.now(timezone.utc) - timedelta(minutes=1),
    )


async def test_publica_articulos_pendientes_de_forma_idempotente():
    post = _scheduled_post("p1")
    repo = FakeRepo([post])

    count = await _publish_due_posts(repo)

    assert count == 1
    assert post.status == "published"
    assert post.scheduled_for is None
    assert post.published_at is not None


async def test_continua_si_un_articulo_falla():
    good = _scheduled_post("ok")
    bad = _scheduled_post("bad")

    class FailingRepo(FakeRepo):
        async def update(self, post):
            if post.id == "bad":
                raise RuntimeError("fallo simulado")
            return await super().update(post)

    repo = FailingRepo([bad, good])
    count = await _publish_due_posts(repo)

    assert count == 1
    assert good.status == "published"
