"""Emails and in-app notifications for user submissions."""

from decimal import Decimal
from types import SimpleNamespace

import asyncio
import functools

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import AuthenticatedUser, get_current_user
from app.main import app
from app.modules.emails.application import rendering
from app.modules.emails.application.rendering import (
    EmailBranding,
    render_submission_admin,
    render_submission_approved,
    render_submission_rejected,
    render_welcome,
)
from app.modules.submissions.api.dependencies import (
    get_profile_repository,
    get_submission_notifier,
    get_submission_repository,
)
from app.modules.submissions.api import schemas
from app.modules.submissions.api.router import get_category_repository
from app.modules.submissions.application import notifier as notifier_module
from app.modules.submissions.application.notifier import SubmissionNotifier

from app.tests.test_submission_create import (
    FakeCategories,
    FakeProfileRepo,
    FakeRepo,
    body,
)

def sync(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))

    return wrapper


XSS = "<script>alert(1)</script>"
BRANDING = EmailBranding()
SUB_ID = "11111111-1111-4111-8111-111111111111"


def test_admin_email_contains_data_and_escapes_html():
    mail = render_submission_admin(
        BRANDING,
        title=XSS,
        price="10,00 €",
        previous_price="20,00 €",
        store="Amazon",
        author=XSS,
        image_url=None,
        review_url="https://x.test/admin/propuestas?id=1",
        warnings=["Tienda sin afiliación"],
    )
    assert mail.subject.startswith("🆕 Nueva propuesta de chollo: ")
    assert "<script>" not in mail.html
    assert "&lt;script&gt;" in mail.html
    assert "10,00 €" in mail.html and "Tienda sin afiliación" in mail.html
    assert "https://x.test/admin/propuestas?id=1" in mail.html
    assert "https://x.test/admin/propuestas?id=1" in mail.text


def test_admin_subject_truncates_title():
    mail = render_submission_admin(
        BRANDING, title="a" * 100, price="1,00 €", previous_price=None, store=None,
        author="p", image_url=None, review_url="u", warnings=[],
    )
    assert mail.subject == "🆕 Nueva propuesta de chollo: " + "a" * 60


def test_approved_email_links_and_escapes():
    mail = render_submission_approved(
        BRANDING, name=XSS, title=XSS, deal_url="https://x.test/chollo/abc"
    )
    assert mail.subject == "✅ Tu chollo ya está publicado"
    assert "<script>" not in mail.html
    assert "https://x.test/chollo/abc" in mail.html and "https://x.test/chollo/abc" in mail.text


def test_rejected_email_has_reason_and_escapes():
    mail = render_submission_rejected(
        BRANDING, name=None, title="Auriculares", reason=XSS, my_deals_url="https://x.test/mis-chollos"
    )
    assert mail.subject == "Tu propuesta de chollo no ha sido publicada"
    assert "<script>" not in mail.html
    assert "&lt;script&gt;" in mail.html
    assert XSS in mail.text
    assert "https://x.test/mis-chollos" in mail.html


def test_welcome_render_unchanged_by_new_templates():
    mail = render_welcome(BRANDING, name="Pedro")
    assert "¡Hola, Pedro!" in mail.html
    assert rendering._env.autoescape("welcome.html.j2") is True


class FakeSender:
    def __init__(self, result=True, error=None):
        self.sent = []
        self.result, self.error = result, error

    def send(self, email):
        return self.result

    async def send_async(self, email):
        if self.error:
            raise self.error
        self.sent.append(email)
        return self.result


class FakeSession:
    def __init__(self):
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def commit(self):
        self.committed = True


def make_sub(status="pending", **over):
    data = dict(
        id=SUB_ID,
        user_id="u1",
        status=status,
        title="Auriculares",
        current_price=Decimal("10"),
        previous_price=Decimal("20"),
        store=SimpleNamespace(name="Amazon"),
        store_name=None,
        user=SimpleNamespace(display_name="Pedro", username="pedro"),
        image_url="https://m.media-amazon.com/images/I/a.jpg",
        warnings=["not_affiliable", "otro"],
        rejection_reason=None,
        deal_id=None,
        deal=None,
    )
    data.update(over)
    return SimpleNamespace(**data)


@pytest.fixture
def env(monkeypatch):
    session = FakeSession()
    created = []

    class Repo:
        sub = make_sub()

        def __init__(self, s):
            pass

        async def get(self, id):
            return Repo.sub

    class NotifRepo:
        def __init__(self, s):
            pass

        async def create(self, data):
            created.append(data)

    monkeypatch.setattr(notifier_module, "SubmissionRepository", Repo)
    monkeypatch.setattr(notifier_module, "NotificationRepository", NotifRepo)
    return SimpleNamespace(session=session, created=created, repo=Repo)


def make_notifier(env, sender, admin_email="admin@x.test", lookup_email="user@x.test"):
    async def lookup(user_id):
        return lookup_email

    return SubmissionNotifier(
        sender,
        BRANDING,
        SimpleNamespace(admin_notification_email=admin_email),
        lookup,
        session_factory=lambda: env.session,
    )


@sync
async def test_notify_admin_sends_to_configured_email(env):
    sender = FakeSender()
    await make_notifier(env, sender).notify_admin_new(SUB_ID)
    assert len(sender.sent) == 1
    mail = sender.sent[0]
    assert mail.to == "admin@x.test"
    assert f"{BRANDING.site_url}/admin/propuestas?id={SUB_ID}" in mail.html
    assert "Pedro" in mail.html and "Amazon" in mail.html
    assert "10,00 €" in mail.html and "20,00 €" in mail.html
    assert "Tienda sin afiliación" in mail.html and "otro" in mail.html


@sync
async def test_notify_admin_skips_when_email_empty(env):
    sender = FakeSender()
    await make_notifier(env, sender, admin_email="").notify_admin_new(SUB_ID)
    assert sender.sent == []


@sync
async def test_notify_admin_falls_back_to_username_and_store_name(env):
    env.repo.sub = make_sub(
        user=SimpleNamespace(display_name=None, username="pedro99"),
        store=None,
        store_name="MiTienda",
    )
    sender = FakeSender()
    await make_notifier(env, sender).notify_admin_new(SUB_ID)
    assert "pedro99" in sender.sent[0].html and "MiTienda" in sender.sent[0].html


@sync
async def test_notify_user_approved_creates_notification_and_email(env):
    env.repo.sub = make_sub("approved", deal_id="d1", deal=SimpleNamespace(slug="auriculares-x"))
    sender = FakeSender()
    await make_notifier(env, sender).notify_user_decision(SUB_ID)
    assert env.created == [
        {
            "user_id": "u1",
            "type": "submission_approved",
            "title": "Tu chollo ya está publicado",
            "body": "Auriculares",
            "link_url": "/chollo/auriculares-x",
            "deal_id": "d1",
        }
    ]
    assert env.session.committed
    assert sender.sent[0].to == "user@x.test"
    assert f"{BRANDING.site_url}/chollo/auriculares-x" in sender.sent[0].html


@sync
async def test_notify_user_rejected_creates_notification_and_email(env):
    env.repo.sub = make_sub("rejected", rejection_reason="Precio no real")
    sender = FakeSender()
    await make_notifier(env, sender).notify_user_decision(SUB_ID)
    assert env.created[0]["type"] == "submission_rejected"
    assert env.created[0]["link_url"] == "/mis-chollos"
    assert "deal_id" not in env.created[0]
    assert "Precio no real" in sender.sent[0].html


@sync
async def test_notify_user_ignores_non_final_status(env):
    sender = FakeSender()
    await make_notifier(env, sender).notify_user_decision(SUB_ID)
    assert env.created == [] and sender.sent == []


@sync
async def test_notify_user_without_email_still_creates_notification(env):
    env.repo.sub = make_sub("rejected", rejection_reason="x")
    sender = FakeSender()
    await make_notifier(env, sender, lookup_email=None).notify_user_decision(SUB_ID)
    assert len(env.created) == 1 and sender.sent == []


@sync
async def test_sender_failure_never_raises(env):
    env.repo.sub = make_sub("rejected", rejection_reason="x")
    sender = FakeSender(error=RuntimeError("smtp down"))
    notifier = make_notifier(env, sender)
    await notifier.notify_admin_new(SUB_ID)
    await notifier.notify_user_decision(SUB_ID)


@sync
async def test_session_failure_never_raises():
    def boom():
        raise RuntimeError("no db")

    async def lookup(user_id):
        return None

    notifier = SubmissionNotifier(
        FakeSender(), BRANDING, SimpleNamespace(admin_notification_email="a@x.test"), lookup,
        session_factory=boom,
    )
    await notifier.notify_admin_new(SUB_ID)
    await notifier.notify_user_decision(SUB_ID)


def _setup_endpoint(events, repo=None, error=None):
    limiter.reset()

    class SpyNotifier:
        async def notify_admin_new(self, submission_id):
            events.append(("task", submission_id))

    class SpyDb:
        async def commit(self):
            events.append(("commit", None))

    repo = repo or FakeRepo()
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id="u1", email="a@b.c")
    app.dependency_overrides[get_profile_repository] = lambda: FakeProfileRepo()
    app.dependency_overrides[get_submission_repository] = lambda: repo
    app.dependency_overrides[get_category_repository] = lambda: FakeCategories()
    app.dependency_overrides[get_submission_notifier] = lambda: SpyNotifier()
    app.dependency_overrides[get_db] = lambda: SpyDb()


@pytest.fixture
def endpoint_settings(monkeypatch):
    monkeypatch.setattr(
        schemas, "get_settings", lambda: SimpleNamespace(supabase_url="https://proj.supabase.co/")
    )
    yield
    app.dependency_overrides.clear()


def test_create_endpoint_commits_before_scheduling_admin_notification(endpoint_settings):
    events = []
    _setup_endpoint(events)
    resp = TestClient(app).post("/v1/submissions", json=body())
    assert resp.status_code == 201, resp.text
    assert events == [("commit", None), ("task", SUB_ID)]


@pytest.mark.parametrize(
    "repo_kwargs, payload, status",
    [
        (dict(live=SimpleNamespace(id="d1", slug="x", title="T", image_url=None, current_price=9.5, status="active")), {}, 409),
        (dict(pending_count=5), {}, 429),
        (dict(day_count=15), {}, 429),
        (dict(), dict(category_id="missing"), 400),
    ],
)
def test_create_endpoint_failure_schedules_nothing(endpoint_settings, repo_kwargs, payload, status):
    events = []
    _setup_endpoint(events, repo=FakeRepo(**repo_kwargs))
    resp = TestClient(app).post("/v1/submissions", json=body(**payload))
    assert resp.status_code == status, resp.text
    assert events == []


def test_admin_subject_collapses_crlf_and_is_sendable():
    from email.message import EmailMessage

    mail = render_submission_admin(
        BRANDING, title="a\r\nBcc: x", price="1,00 €", previous_price=None, store=None,
        author="p", image_url=None, review_url="u", warnings=[],
    )
    assert "\r" not in mail.subject and "\n" not in mail.subject
    assert mail.subject == "🆕 Nueva propuesta de chollo: a Bcc: x"
    msg = EmailMessage()
    msg["Subject"] = mail.subject


@sync
async def test_crlf_title_reaches_sender(env):
    env.repo.sub = make_sub(title="a\r\nBcc: x")
    sender = FakeSender()
    await make_notifier(env, sender).notify_admin_new(SUB_ID)
    assert len(sender.sent) == 1 and "\n" not in sender.sent[0].subject


@sync
async def test_missing_submission_logs_warning(env, caplog):
    env.repo.sub = None
    sender = FakeSender()
    notifier = make_notifier(env, sender)
    await notifier.notify_admin_new(SUB_ID)
    await notifier.notify_user_decision(SUB_ID)
    assert caplog.text.count("no encontrada") == 2
    assert sender.sent == []


@sync
async def test_approved_without_deal_logs_warning(env, caplog):
    env.repo.sub = make_sub("approved", deal=None)
    sender = FakeSender()
    await make_notifier(env, sender).notify_user_decision(SUB_ID)
    assert "sin chollo asociado" in caplog.text
    assert env.created == [] and sender.sent == []
