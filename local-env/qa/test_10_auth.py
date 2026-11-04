"""Acceso: sin sesión, tokens falsos o caducados, y endpoints de admin para no-admins."""

import base64
import json
import time

import jwt
import pytest

from conftest import Api, assert_no_5xx

USER_ENDPOINTS = [
    ("post", "/v1/submissions/check-link", {"json": {"url": "https://www.amazon.es/dp/B09B8X9RGM"}}),
    ("post", "/v1/submissions", {"json": {}}),
    ("get", "/v1/submissions/mine", {}),
    ("delete", "/v1/submissions/00000000-0000-0000-0000-000000000000", {}),
    ("post", "/v1/submissions/images/from-url", {"json": {"url": "https://m.media-amazon.com/images/I/x.jpg"}}),
    ("post", "/v1/submissions/images", {"files": {"file": ("a.png", b"x", "image/png")}}),
]

ADMIN_ENDPOINTS = [
    ("get", "/v1/admin/submissions", {}),
    ("get", "/v1/admin/submissions/count", {}),
    ("get", "/v1/admin/submissions/00000000-0000-0000-0000-000000000000", {}),
    ("post", "/v1/admin/submissions/00000000-0000-0000-0000-000000000000/approve", {"json": {}}),
    ("post", "/v1/admin/submissions/00000000-0000-0000-0000-000000000000/reject", {"json": {"reason": "nope"}}),
]


def _forged_token(sub: str, **claims) -> str:
    payload = {"sub": sub, "aud": "authenticated", "exp": int(time.time()) + 3600, **claims}
    return jwt.encode(payload, "clave-que-no-es-la-de-supabase", algorithm="HS256")


@pytest.mark.parametrize("method,path,kw", USER_ENDPOINTS)
def test_anonymous_is_rejected(anon, method, path, kw):
    resp = getattr(anon, method)(path, **kw)
    assert resp.status_code in (401, 403), resp.text


@pytest.mark.parametrize(
    "token",
    [
        "no-es-un-jwt",
        "a.b.c",
        "Bearer",
    ],
)
def test_garbage_tokens_get_401(token):
    resp = Api(token).get("/v1/submissions/mine")
    assert resp.status_code in (401, 403), resp.text


def test_forged_signature_is_rejected(users):
    resp = Api(_forged_token(users[0].id)).get("/v1/submissions/mine")
    assert resp.status_code == 401, resp.text


def test_alg_none_token_is_rejected(users):
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=")
    body = base64.urlsafe_b64encode(
        json.dumps({"sub": users[0].id, "aud": "authenticated", "exp": int(time.time()) + 3600}).encode()
    ).rstrip(b"=")
    resp = Api(f"{header.decode()}.{body.decode()}.").get("/v1/submissions/mine")
    assert resp.status_code == 401, resp.text


def test_tampered_payload_is_rejected(users, admin):
    """Cambiar el sub de un token válido (sin re-firmar) debe invalidarlo."""
    head, body, sig = users[0].token.split(".")
    claims = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    claims["sub"] = admin.id
    forged = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    resp = Api(f"{head}.{forged}.{sig}").get("/v1/admin/submissions")
    assert resp.status_code == 401, resp.text


@pytest.mark.parametrize("method,path,kw", ADMIN_ENDPOINTS)
def test_regular_user_cannot_use_admin_endpoints(users, method, path, kw):
    resp = getattr(users[0], method)(path, **kw)
    assert_no_5xx(resp)
    assert resp.status_code in (403, 422), resp.text
    # 422 solo es aceptable si es validación de body ANTES de comprobar el rol;
    # en ningún caso debe devolver datos.
    assert "original_url" not in resp.text


@pytest.mark.parametrize("method,path,kw", ADMIN_ENDPOINTS)
def test_anonymous_cannot_use_admin_endpoints(anon, method, path, kw):
    resp = getattr(anon, method)(path, **kw)
    assert resp.status_code in (401, 403), resp.text


def test_admin_can_list(admin):
    resp = admin.get("/v1/admin/submissions")
    assert resp.status_code == 200, resp.text
    count = admin.get("/v1/admin/submissions/count")
    assert count.status_code == 200 and "pending" in count.json(), count.text
