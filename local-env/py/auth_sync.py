"""Refleja en la base local los usuarios de Supabase Auth que se usan en local.

La web local hace login contra el Supabase Auth REAL; la API local valida el
JWT con la clave pública de Supabase, pero busca perfil y roles en la base
LOCAL. En producción el trigger `on_auth_user_created` crea ese perfil al
registrarse; aquí este script inserta el usuario en la tabla local
`auth.users` y el MISMO trigger (reproducido por las migraciones) crea el
perfil y el rol `user`.

Solo se reflejan (para no bajar datos personales de terceros):
  - los correos de `admin_emails` (config.json), que además reciben rol admin;
  - los que encajan con `sync_email_patterns` (alias de prueba);
  - cualquier cuenta creada DESPUÉS de montar la base local (te registras
    desde http://localhost:8080 y a los pocos segundos ya existe en local).

Los usuarios borrados en Supabase Auth se borran también en local.

Modo bucle (`python auth_sync.py --loop`): sincroniza cada 3 s.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime

import asyncpg
import httpx

from common import (
    email_matches,
    load_config,
    local_dsn,
    read_state,
    supabase_service_key,
    supabase_url,
)

SYNC_INTERVAL_SECONDS = 3


async def _remote_users(client: httpx.AsyncClient) -> list[dict]:
    key = supabase_service_key()
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    users: list[dict] = []
    page = 1
    while True:
        resp = await client.get(
            f"{supabase_url()}/auth/v1/admin/users",
            params={"page": page, "per_page": 1000},
            headers=headers,
        )
        resp.raise_for_status()
        batch = resp.json().get("users", [])
        users.extend(batch)
        if len(batch) < 1000:
            return users
        page += 1


def _wanted(user: dict, config: dict, since: datetime | None) -> bool:
    email = user.get("email")
    if email_matches(email, config["admin_emails"]) or email_matches(email, config["sync_email_patterns"]):
        return True
    created = user.get("created_at")
    return bool(since and created and datetime.fromisoformat(created.replace("Z", "+00:00")) >= since)


async def sync_once(verbose: bool = False, client: httpx.AsyncClient | None = None) -> None:
    config = load_config()
    created_at = read_state().get("db_created_at")
    since = datetime.fromisoformat(created_at) if created_at else None

    own_client = client is None
    client = client or httpx.AsyncClient(timeout=15)
    try:
        remote = await _remote_users(client)
    finally:
        if own_client:
            await client.aclose()

    remote_ids = {u["id"] for u in remote}
    wanted = [u for u in remote if _wanted(u, config, since)]
    admin_emails = {e.lower() for e in config["admin_emails"]}

    conn = await asyncpg.connect(local_dsn())
    try:
        local_ids = {str(r["id"]) for r in await conn.fetch("SELECT id FROM auth.users")}
        for user in wanted:
            await conn.execute(
                """
                INSERT INTO auth.users (id, email, raw_user_meta_data, raw_app_meta_data, created_at)
                VALUES ($1, $2, $3::jsonb, $4::jsonb, $5::timestamptz)
                ON CONFLICT (id) DO UPDATE
                  SET email = EXCLUDED.email,
                      raw_user_meta_data = EXCLUDED.raw_user_meta_data,
                      raw_app_meta_data = EXCLUDED.raw_app_meta_data,
                      updated_at = now()
                """,
                user["id"],
                user.get("email"),
                json.dumps(user.get("user_metadata") or {}),
                json.dumps(user.get("app_metadata") or {}),
                datetime.fromisoformat(user["created_at"].replace("Z", "+00:00")),
            )
            if (user.get("email") or "").lower() in admin_emails:
                await conn.execute(
                    "INSERT INTO public.user_roles (user_id, role) VALUES ($1, 'admin') ON CONFLICT DO NOTHING",
                    user["id"],
                )
            if user["id"] not in local_ids:
                print(f"[auth-sync] usuario añadido en local: {user.get('email')}", flush=True)

        gone = sorted(local_ids - remote_ids)
        if gone:
            await conn.execute("DELETE FROM auth.users WHERE id = ANY($1::uuid[])", gone)
            print(f"[auth-sync] {len(gone)} usuario(s) borrado(s) en Supabase → borrado(s) en local", flush=True)
        if verbose:
            print(f"  usuarios reflejados: {len(wanted)}")
    finally:
        await conn.close()


async def loop() -> None:
    print(f"[auth-sync] activo: usuarios cada {SYNC_INTERVAL_SECONDS}s", flush=True)
    async with httpx.AsyncClient(timeout=15) as client:
        while True:
            try:
                await sync_once(client=client)
            except Exception as exc:  # el bucle no debe morir por un fallo de red puntual
                print(f"[auth-sync] error sincronizando usuarios: {type(exc).__name__}: {exc}", flush=True)
            await asyncio.sleep(SYNC_INTERVAL_SECONDS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true")
    if parser.parse_args().loop:
        asyncio.run(loop())
    else:
        asyncio.run(sync_once(verbose=True))
