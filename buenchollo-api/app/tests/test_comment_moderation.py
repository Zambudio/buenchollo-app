"""Tests unitarios (sin BD) de la moderación admin y el rate limit de votos
de comentarios de chollos y de blog."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.main import app
from app.modules.blog_comments.api.router import get_blog_comment_repository
from app.modules.comments.api.router import get_comment_repository


class FakeUser:
    id = "dbe6e006-4f3e-4be8-8351-7e264ed3acb6"


async def _fake_user():
    return FakeUser()


def _fake_comment(**extra):
    c = MagicMock()
    c.id = str(uuid.uuid4())
    c.user_id = "11111111-1111-1111-1111-111111111111"  # autor distinto del admin
    c.deal_id = "22222222-2222-2222-2222-222222222222"
    c.blog_post_id = "33333333-3333-3333-3333-333333333333"
    for k, v in extra.items():
        setattr(c, k, v)
    return c


def _fake_repo(comment):
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=comment)
    repo.delete = AsyncMock()
    repo.recalculate_comment_count = AsyncMock()
    repo.get_user_vote = AsyncMock(return_value=None)
    repo.upsert_vote = AsyncMock()
    repo.delete_vote = AsyncMock()
    repo.recalculate_votes = AsyncMock(return_value={"votes_up": 0, "votes_down": 0})
    return repo


def _fake_db(is_admin: bool):
    db = MagicMock()
    result = MagicMock()
    result.scalar.return_value = 1 if is_admin else None
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def _setup(repo_dep, repo, *, admin: bool = True, authenticated: bool = True):
    app.dependency_overrides[repo_dep] = lambda: repo
    app.dependency_overrides[get_db] = lambda: _fake_db(admin)
    if authenticated:
        app.dependency_overrides[get_current_user] = _fake_user
    return repo


# ── Chollos ──────────────────────────────────────────────────────────────────

def test_admin_borra_comentario_ajeno_de_chollo(client):
    comment = _fake_comment()
    repo = _setup(get_comment_repository, _fake_repo(comment))
    with patch("app.modules.comments.api.router.audit_log", new=AsyncMock()) as audit:
        r = client.delete(f"/v1/deals/admin/comments/{comment.id}")
    assert r.status_code == 204, r.text
    repo.delete.assert_awaited_once_with(comment)
    repo.recalculate_comment_count.assert_awaited_once_with(comment.deal_id)
    audit.assert_awaited_once()
    assert audit.await_args.kwargs["action"] == "comment.delete"
    assert audit.await_args.kwargs["target_id"] == comment.id


def test_no_admin_no_puede_borrar_comentario_de_chollo(client):
    comment = _fake_comment()
    repo = _setup(get_comment_repository, _fake_repo(comment), admin=False)
    r = client.delete(f"/v1/deals/admin/comments/{comment.id}")
    assert r.status_code == 403
    repo.delete.assert_not_awaited()


def test_sin_autenticar_no_puede_borrar_comentario_de_chollo(client):
    repo = _setup(get_comment_repository, _fake_repo(_fake_comment()), authenticated=False)
    r = client.delete(f"/v1/deals/admin/comments/{uuid.uuid4()}")
    assert r.status_code in (401, 403)
    repo.delete.assert_not_awaited()


def test_admin_borrar_comentario_inexistente_de_chollo_da_404(client):
    _setup(get_comment_repository, _fake_repo(None))
    with patch("app.modules.comments.api.router.audit_log", new=AsyncMock()) as audit:
        r = client.delete(f"/v1/deals/admin/comments/{uuid.uuid4()}")
    assert r.status_code == 404
    audit.assert_not_awaited()


# ── Blog ─────────────────────────────────────────────────────────────────────

def test_admin_borra_comentario_ajeno_de_blog(client):
    comment = _fake_comment()
    repo = _setup(get_blog_comment_repository, _fake_repo(comment))
    with patch("app.modules.blog_comments.api.router.audit_log", new=AsyncMock()) as audit:
        r = client.delete(f"/v1/blog/admin/comments/{comment.id}")
    assert r.status_code == 204, r.text
    repo.delete.assert_awaited_once_with(comment)
    audit.assert_awaited_once()
    assert audit.await_args.kwargs["action"] == "blog.comment.delete"


def test_no_admin_no_puede_borrar_comentario_de_blog(client):
    comment = _fake_comment()
    repo = _setup(get_blog_comment_repository, _fake_repo(comment), admin=False)
    r = client.delete(f"/v1/blog/admin/comments/{comment.id}")
    assert r.status_code == 403
    repo.delete.assert_not_awaited()


def test_sin_autenticar_no_puede_borrar_comentario_de_blog(client):
    repo = _setup(get_blog_comment_repository, _fake_repo(_fake_comment()), authenticated=False)
    r = client.delete(f"/v1/blog/admin/comments/{uuid.uuid4()}")
    assert r.status_code in (401, 403)
    repo.delete.assert_not_awaited()


def test_admin_borrar_comentario_inexistente_de_blog_da_404(client):
    _setup(get_blog_comment_repository, _fake_repo(None))
    with patch("app.modules.blog_comments.api.router.audit_log", new=AsyncMock()):
        r = client.delete(f"/v1/blog/admin/comments/{uuid.uuid4()}")
    assert r.status_code == 404


# ── Rate limit de votos ──────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "repo_dep,url",
    [
        (get_comment_repository, "/v1/deals/comments/{id}/vote"),
        (get_blog_comment_repository, "/v1/blog/comments/{id}/vote"),
    ],
)
def test_voto_de_comentario_tiene_rate_limit_30_por_minuto(client, repo_dep, url):
    from app.core.rate_limit import limiter

    comment = _fake_comment()
    _setup(repo_dep, _fake_repo(comment))
    limiter.reset()
    try:
        codes = [
            client.post(url.format(id=comment.id), json={"vote": 1}).status_code
            for _ in range(31)
        ]
    finally:
        limiter.reset()
    assert codes[:30] == [200] * 30
    assert codes[30] == 429
