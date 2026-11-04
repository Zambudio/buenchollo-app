"""Usuarios de prueba para el entorno local (y para las pruebas automáticas).

Crea cuentas REALES en Supabase Auth con alias `pjzambudio+local-<n>@gmail.com`
(configurable con `sync_email_patterns` / `test_email_template` en
config.json), ya confirmadas, con contraseña aleatoria. auth_sync.py las
refleja en la base local en ~3 s. Las credenciales y tokens se guardan en
%LOCALAPPDATA%\\BuenCholloLocal\\test-users.json (fuera del repo).

  python test_users.py create 3      crea 3 usuarios (o completa hasta 3)
  python test_users.py tokens        refresca los access tokens y los imprime en JSON
  python test_users.py delete        borra los usuarios de prueba en Supabase Auth
                                     y sus imágenes de propuestas en Storage

Puedes entrar en http://localhost:8080 con cualquiera de ellos: el correo y la
contraseña están en test-users.json.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import secrets
import sys

import asyncpg
import httpx
from dotenv import dotenv_values

from common import RUNTIME_DIR, WEB_DIR, load_config, local_dsn, supabase_service_key, supabase_url

USERS_FILE = RUNTIME_DIR / "test-users.json"
BUCKET = "deal-images"


def _admin_headers() -> dict[str, str]:
    key = supabase_service_key()
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def _anon_key() -> str:
    return dotenv_values(WEB_DIR / ".env", encoding="utf-8-sig").get("VITE_SUPABASE_PUBLISHABLE_KEY") or ""


def _load() -> list[dict]:
    return json.loads(USERS_FILE.read_text(encoding="utf-8")) if USERS_FILE.exists() else []


def _save(users: list[dict]) -> None:
    USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")


async def _password_token(client: httpx.AsyncClient, email: str, password: str) -> str:
    resp = await client.post(
        f"{supabase_url()}/auth/v1/token",
        params={"grant_type": "password"},
        headers={"apikey": _anon_key()},
        json={"email": email, "password": password},
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


async def _wait_local(user_ids: list[str], timeout: float = 30) -> None:
    """Espera a que auth_sync haya reflejado los usuarios (perfil creado por trigger)."""
    conn = await asyncpg.connect(local_dsn())
    try:
        for _ in range(int(timeout * 2)):
            n = await conn.fetchval("SELECT count(*) FROM public.profiles WHERE user_id = ANY($1::uuid[])", user_ids)
            if n == len(user_ids):
                return
            await asyncio.sleep(0.5)
    finally:
        await conn.close()
    raise SystemExit("auth_sync no ha reflejado los usuarios: ¿está el entorno arrancado? (bct-local.ps1 start)")


async def create(count: int) -> None:
    template = load_config().get("test_email_template", "pjzambudio+local-{n}@gmail.com")
    users = _load()
    async with httpx.AsyncClient(timeout=20) as client:
        n = len(users) + 1
        while len(users) < count:
            email = template.format(n=n)
            password = secrets.token_urlsafe(18)
            resp = await client.post(
                f"{supabase_url()}/auth/v1/admin/users",
                headers=_admin_headers(),
                json={
                    "email": email,
                    "password": password,
                    "email_confirm": True,
                    "user_metadata": {"display_name": f"Tester Local {n}"},
                },
            )
            if resp.status_code == 422 and "already" in resp.text:
                print(f"  {email} ya existe en Supabase Auth y no está en test-users.json: sáltalo o bórralo a mano")
                n += 1
                continue
            resp.raise_for_status()
            users.append({"email": email, "password": password, "id": resp.json()["id"]})
            print(f"  creado {email}")
            n += 1
        _save(users)
    await _wait_local([u["id"] for u in users])
    print(f"✓ {len(users)} usuario(s) de prueba listos (credenciales en {USERS_FILE})")


async def tokens() -> list[str]:
    users = _load()
    async with httpx.AsyncClient(timeout=20) as client:
        result = [await _password_token(client, u["email"], u["password"]) for u in users]
    return result


async def delete() -> None:
    users = _load()
    async with httpx.AsyncClient(timeout=30) as client:
        for u in users:
            # Imágenes subidas por el usuario en propuestas (Storage real).
            listed = await client.post(
                f"{supabase_url()}/storage/v1/object/list/{BUCKET}",
                headers=_admin_headers(),
                json={"prefix": f"submissions/{u['id']}/", "limit": 1000},
            )
            names = [f"submissions/{u['id']}/{o['name']}" for o in (listed.json() if listed.is_success else [])]
            if names:
                await client.request(
                    "DELETE",
                    f"{supabase_url()}/storage/v1/object/{BUCKET}",
                    headers=_admin_headers(),
                    json={"prefixes": names},
                )
            resp = await client.delete(f"{supabase_url()}/auth/v1/admin/users/{u['id']}", headers=_admin_headers())
            if resp.status_code not in (200, 404):
                resp.raise_for_status()
            print(f"  borrado {u['email']} ({len(names)} imagen(es) en Storage)")
    USERS_FILE.unlink(missing_ok=True)
    print("✓ Usuarios de prueba borrados (auth_sync los quita de la base local en ~3 s)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("create").add_argument("count", type=int, nargs="?", default=3)
    sub.add_parser("tokens")
    sub.add_parser("delete")
    args = parser.parse_args()
    if args.cmd == "create":
        asyncio.run(create(args.count))
    elif args.cmd == "tokens":
        json.dump(asyncio.run(tokens()), sys.stdout)
    else:
        asyncio.run(delete())


if __name__ == "__main__":
    main()
