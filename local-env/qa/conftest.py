"""Pruebas EN VIVO contra el entorno local (API en :8000, Postgres local, correo local).

No son tests unitarios: hablan HTTP con la API real levantada por
`bct-local.ps1 start`, con usuarios reales de Supabase Auth
(`bct-local.ps1 users create 6`). Solo escriben en la base LOCAL; lo único
externo que tocan es Supabase Storage (imágenes de propuestas, que borra
`bct-local.ps1 users delete`) y la Creators API de Amazon (lecturas).

Uso:  & $env:LOCALAPPDATA\\BuenCholloLocal\\api-venv\\Scripts\\python.exe -m pytest local-env/qa -v
      (o `.\\local-env\\bct-local.ps1 qa`)

El usuario de prueba nº 1 recibe rol admin SOLO en la base local durante la
sesión; los límites por usuario (rate limit y cupos) se reparten entre los 6.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

import asyncpg
import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "py"))

import test_users  # noqa: E402
from common import load_config, local_dsn  # noqa: E402

CONFIG = load_config()
API = os.environ.get("BCT_QA_API", f"http://localhost:{CONFIG['api_port']}")
MAIL = os.environ.get("BCT_QA_MAIL", f"http://localhost:{CONFIG['mail_web_port']}")
MIN_USERS = 6


def db(query: str, *args):
    """Consulta síncrona a la base LOCAL (devuelve filas)."""

    async def run():
        conn = await asyncpg.connect(local_dsn())
        try:
            return await conn.fetch(query, *args)
        finally:
            await conn.close()

    return asyncio.run(run())


class Api:
    """Cliente HTTP con el token de un usuario concreto (o anónimo)."""

    def __init__(self, token: str | None, user_id: str | None = None, email: str | None = None):
        self.token = token
        self.id = user_id
        self.email = email
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self.http = httpx.Client(base_url=API, headers=headers, timeout=90)

    def get(self, path, **kw):
        return self.http.get(path, **kw)

    def post(self, path, **kw):
        return self.http.post(path, **kw)

    def put(self, path, **kw):
        return self.http.put(path, **kw)

    def delete(self, path, **kw):
        return self.http.delete(path, **kw)


class Mail:
    def messages(self) -> list[dict]:
        return httpx.get(f"{MAIL}/api/messages", timeout=10).json()

    def wait_for(self, predicate, timeout: float = 20) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for m in self.messages():
                if predicate(m):
                    return m
            time.sleep(0.5)
        raise AssertionError("No ha llegado el correo esperado al capturador local")

    def clear(self) -> None:
        httpx.post(f"{MAIL}/api/clear", timeout=10, follow_redirects=False)


def _cleanup(user_ids: list[str]) -> None:
    db(
        """
        DELETE FROM public.deals WHERE id IN (
          SELECT deal_id FROM public.deal_submissions WHERE user_id = ANY($1::uuid[]) AND deal_id IS NOT NULL
        ) OR created_by = ANY($1::uuid[])
        """,
        user_ids,
    )
    db("DELETE FROM public.deal_submissions WHERE user_id = ANY($1::uuid[])", user_ids)
    db("DELETE FROM public.notifications WHERE user_id = ANY($1::uuid[])", user_ids)


@pytest.fixture(scope="session")
def test_accounts() -> list[dict]:
    accounts = test_users._load()
    if len(accounts) < MIN_USERS:
        pytest.exit(f"Hacen falta {MIN_USERS} usuarios de prueba: .\\local-env\\bct-local.ps1 users create {MIN_USERS}")
    try:
        httpx.get(f"{API}/health", timeout=5).raise_for_status()
    except Exception:
        pytest.exit(f"La API local no responde en {API}: .\\local-env\\bct-local.ps1 start")
    return accounts


@pytest.fixture(scope="session")
def tokens(test_accounts) -> list[str]:
    return asyncio.run(test_users.tokens())


@pytest.fixture(scope="session", autouse=True)
def session_state(test_accounts):
    ids = [a["id"] for a in test_accounts]
    _cleanup(ids)
    # Perfiles completos (el trigger ya pone display_name) y rol admin LOCAL al nº 1.
    db("UPDATE public.profiles SET display_name = 'Tester Local ' || right(user_id::text, 4) "
       "WHERE user_id = ANY($1::uuid[]) AND coalesce(display_name, '') = ''", ids)
    db("INSERT INTO public.user_roles (user_id, role) VALUES ($1, 'admin') ON CONFLICT DO NOTHING", ids[0])
    yield
    db("DELETE FROM public.user_roles WHERE user_id = $1 AND role = 'admin'", ids[0])
    _cleanup(ids)


@pytest.fixture(scope="session")
def admin(test_accounts, tokens) -> Api:
    a = test_accounts[0]
    return Api(tokens[0], a["id"], a["email"])


@pytest.fixture(scope="session")
def users(test_accounts, tokens) -> list[Api]:
    """Usuarios normales (sin admin): índices 0..4 → cuentas 2..6."""
    return [Api(t, a["id"], a["email"]) for a, t in zip(test_accounts[1:], tokens[1:])]


class Pool:
    """Reparte peticiones entre las cuentas sin superar el rate limit por usuario.

    Límites de app/modules/submissions/api/router.py (por usuario y minuto).
    Se cuenta en ventana deslizante de 60 s, más estricta que la ventana fija
    de slowapi, y se deja 1 de margen. Las peticiones con error de validación
    también cuentan en la API, así que también aquí.
    """

    LIMITS = {"check": 20, "create": 10, "images": 30, "images-url": 30}

    def __init__(self, accounts: list[Api]):
        self.accounts = accounts
        self.hits: dict[tuple[str, str], list[float]] = {}
        self.cursor = 0

    def next(self, scope: str) -> Api:
        limit = self.LIMITS[scope] - 1
        while True:
            now = time.monotonic()
            for _ in range(len(self.accounts)):
                acc = self.accounts[self.cursor % len(self.accounts)]
                self.cursor += 1
                stamps = [t for t in self.hits.get((acc.id, scope), []) if now - t < 61]
                if len(stamps) < limit:
                    stamps.append(now)
                    self.hits[(acc.id, scope)] = stamps
                    return acc
            oldest = min(min(v) for k, v in self.hits.items() if k[1] == scope)
            time.sleep(max(0.5, 61 - (now - oldest)))

    def reserve(self, acc: Api, scope: str, n: int) -> None:
        """Espera a que `acc` tenga hueco para `n` peticiones seguidas y las anota."""
        while True:
            now = time.monotonic()
            stamps = [t for t in self.hits.get((acc.id, scope), []) if now - t < 61]
            if len(stamps) + n <= self.LIMITS[scope] - 1 or not stamps:
                self.hits[(acc.id, scope)] = stamps + [now] * n
                return
            time.sleep(max(0.5, 61 - (now - min(stamps))))

    def drain(self, acc: Api, scope: str) -> None:
        """Espera a que `acc` no tenga peticiones recientes en `scope` (ventana limpia)."""
        stamps = self.hits.get((acc.id, scope), [])
        if stamps:
            time.sleep(max(0.0, 62 - (time.monotonic() - max(stamps))))
        self.hits[(acc.id, scope)] = []


@pytest.fixture(scope="session")
def pool(admin, users) -> Pool:
    return Pool([*users, admin])


@pytest.fixture(scope="session")
def anon() -> Api:
    return Api(None)


@pytest.fixture(scope="session")
def mail() -> Mail:
    return Mail()


@pytest.fixture(scope="session")
def category() -> dict:
    row = db(
        """
        SELECT c.id::text AS id, (SELECT s.id::text FROM public.categories s
                                  WHERE s.parent_id = c.id AND s.is_active ORDER BY s.name LIMIT 1) AS sub
        FROM public.categories c
        WHERE c.parent_id IS NULL AND c.is_active
          AND EXISTS (SELECT 1 FROM public.categories s WHERE s.parent_id = c.id)
        ORDER BY c.name LIMIT 1
        """
    )[0]
    return {"category_id": row["id"], "subcategory_id": row["sub"]}


@pytest.fixture
def unique() -> str:
    return str(int(time.time() * 1000))


def submission_payload(category: dict, url: str, **overrides) -> dict:
    body = {
        "url": url,
        "title": "Producto de prueba QA",
        "description": "Descripción de prueba",
        "current_price": "19.99",
        "previous_price": "29.99",
        "category_id": category["category_id"],
        "subcategory_id": category["subcategory_id"],
        "images": [],
    }
    body.update(overrides)
    return body


def assert_no_5xx(resp: httpx.Response) -> None:
    assert resp.status_code < 500, f"{resp.status_code} {resp.text[:300]}"


def detail(resp: httpx.Response) -> str:
    try:
        return json.dumps(resp.json(), ensure_ascii=False)
    except ValueError:
        return resp.text
