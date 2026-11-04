"""Construye la base de datos local desde cero, calcada de producción.

Pasos:
  1. Recrea la base `buenchollo_local` en el Postgres local.
  2. Aplica la capa de Supabase (sql/supabase_shim.sql).
  3. Restaura el esquema `public` REAL de producción (pg_dump --schema-only).
     No se reproducen las migraciones de buenchollo-api/supabase/migrations:
     no coinciden con lo que hay en producción (enums que allí son text,
     triggers que allí no existen...). Ver docs/guides/LOCAL-ENV.md.
  4. Sincroniza los usuarios de Auth permitidos (auth_sync.sync_once).
  5. Copia de producción, en SOLO LECTURA, las tablas de catálogo de
     config.json, la versión de Alembic y el perfil/roles de los admins. No
     copia datos personales de otros usuarios.
  6. `alembic upgrade head`: aplica las migraciones de la rama actual que
     aún no estén en producción, como haría el contenedor al desplegar.

Uso (con el python del venv local):  python db_setup.py
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from urllib.parse import unquote, urlparse

import asyncpg

import auth_sync
from common import (
    API_DIR,
    LOCAL_ENV_DIR,
    PG_DB,
    PG_HOST,
    PG_PORT,
    PG_USER,
    RUNTIME_DIR,
    load_config,
    local_dsn,
    local_sqlalchemy_url,
    prod_dsn,
    utcnow,
    write_state,
)

PG_BIN = RUNTIME_DIR / "pgsql" / "bin"
SCHEMA_DUMP = RUNTIME_DIR / "prod_public_schema.sql"


def _run(cmd: list[str], env: dict | None = None, cwd=None) -> None:
    result = subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        print(result.stdout[-2000:], result.stderr[-4000:], sep="\n")
        raise SystemExit(f"{os.path.basename(cmd[0])} falló")


def dump_prod_schema() -> None:
    """pg_dump del schema public de producción (solo estructura, sin datos)."""
    url = urlparse(prod_dsn())
    host, port = url.hostname or "", str(url.port or 5432)
    user, database = unquote(url.username or ""), url.path.lstrip("/") or "postgres"

    # La contraseña va en un pgpass temporal en UTF-8: por variable de entorno
    # o argumento, Windows la convierte a la página de códigos ANSI y los
    # caracteres no ASCII (p. ej. '€') llegan corruptos a libpq.
    def esc(value: str) -> str:
        return value.replace("\\", "\\\\").replace(":", "\\:")

    pgpass = RUNTIME_DIR / "prod.pgpass"
    pgpass.write_text(
        ":".join(esc(v) for v in (host, port, database, user, unquote(url.password or ""))) + "\n",
        encoding="utf-8",
    )
    env = {
        **os.environ,
        "PGPASSFILE": str(pgpass),
        "PGSSLMODE": "require",
        "PGOPTIONS": "-c default_transaction_read_only=on",
    }
    try:
        _run(
            [
                str(PG_BIN / "pg_dump.exe"),
                "--host", host, "--port", port, "--username", user, "--dbname", database,
                "--schema-only", "--schema=public",
                "--no-owner", "--no-privileges", "--no-publications", "--no-subscriptions",
                "--file", str(SCHEMA_DUMP),
            ],
            env=env,
        )
    finally:
        pgpass.unlink(missing_ok=True)
    # `public` ya existe en una base nueva.
    sql = SCHEMA_DUMP.read_text(encoding="utf-8")
    sql = sql.replace("CREATE SCHEMA public;", "-- CREATE SCHEMA public; (ya existe)")
    SCHEMA_DUMP.write_text(sql, encoding="utf-8")


def _psql_file(path) -> None:
    _run(
        [
            str(PG_BIN / "psql.exe"),
            "-h", PG_HOST, "-p", str(PG_PORT), "-U", PG_USER, "-d", PG_DB,
            "-v", "ON_ERROR_STOP=1", "-q", "-f", str(path),
        ]
    )


async def recreate_database() -> None:
    admin = await asyncpg.connect(local_dsn("postgres"))
    try:
        await admin.execute(f'DROP DATABASE IF EXISTS "{PG_DB}" WITH (FORCE)')
        await admin.execute(f'CREATE DATABASE "{PG_DB}" ENCODING \'UTF8\' TEMPLATE template0')
        await admin.execute(f'ALTER DATABASE "{PG_DB}" SET search_path = "$user", public, extensions')
    finally:
        await admin.close()


async def build_schema() -> None:
    _psql_file(LOCAL_ENV_DIR / "sql" / "supabase_shim.sql")
    dump_prod_schema()
    _psql_file(SCHEMA_DUMP)
    conn = await asyncpg.connect(local_dsn())
    try:
        # El trigger de alta vive en el schema auth (fuera del volcado de public).
        await conn.execute(
            "CREATE TRIGGER on_auth_user_created AFTER INSERT ON auth.users "
            "FOR EACH ROW EXECUTE FUNCTION public.handle_new_user()"
        )
    finally:
        await conn.close()


async def _columns(conn: asyncpg.Connection, table: str) -> list[str]:
    rows = await conn.fetch(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = $1 AND is_generated = 'NEVER'
        ORDER BY ordinal_position
        """,
        table,
    )
    return [r["column_name"] for r in rows]


async def _copy_rows(prod, local, table: str, where: str = "", args: tuple = ()) -> int:
    cols = await _columns(local, table)
    col_sql = ", ".join(f'"{c}"' for c in cols)
    rows = await prod.fetch(f"SELECT {col_sql} FROM public.{table} {where}", *args)
    if rows:
        await local.copy_records_to_table(table, schema_name="public", columns=cols, records=rows)
    return len(rows)


async def _fix_orphans(local, tables: list[str]) -> None:
    """Anula (o borra, si la columna es NOT NULL) referencias a filas no copiadas."""
    fks = await local.fetch(
        """
        SELECT cl.relname AS tbl, att.attname AS col, att.attnotnull AS notnull,
               rn.nspname AS ref_schema, rcl.relname AS ref_tbl, ratt.attname AS ref_col
        FROM pg_constraint con
        JOIN pg_class cl ON cl.oid = con.conrelid
        JOIN pg_namespace n ON n.oid = cl.relnamespace AND n.nspname = 'public'
        JOIN pg_class rcl ON rcl.oid = con.confrelid
        JOIN pg_namespace rn ON rn.oid = rcl.relnamespace
        JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = con.conkey[1]
        JOIN pg_attribute ratt ON ratt.attrelid = con.confrelid AND ratt.attnum = con.confkey[1]
        WHERE con.contype = 'f' AND array_length(con.conkey, 1) = 1 AND cl.relname = ANY($1::text[])
        """,
        tables,
    )
    for fk in fks:
        orphan = (
            f'"{fk["col"]}" IS NOT NULL AND NOT EXISTS (SELECT 1 FROM "{fk["ref_schema"]}"."{fk["ref_tbl"]}" r '
            f'WHERE r."{fk["ref_col"]}" = t."{fk["col"]}")'
        )
        if fk["notnull"]:
            status = await local.execute(f'DELETE FROM public."{fk["tbl"]}" t WHERE {orphan}')
        else:
            status = await local.execute(f'UPDATE public."{fk["tbl"]}" t SET "{fk["col"]}" = NULL WHERE {orphan}')
        affected = int(status.split()[-1])
        if affected:
            action = "borradas" if fk["notnull"] else "anuladas"
            print(f"    {fk['tbl']}.{fk['col']}: {affected} referencia(s) a {fk['ref_tbl']} no copiadas ({action})")


async def _reset_sequences(local, tables: list[str]) -> None:
    rows = await local.fetch(
        """
        SELECT table_name, column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = ANY($1::text[])
          AND (column_default LIKE 'nextval(%' OR is_identity = 'YES')
        """,
        tables,
    )
    for r in rows:
        await local.execute(
            f"SELECT setval(pg_get_serial_sequence('public.\"{r['table_name']}\"', '{r['column_name']}'), "
            f"COALESCE((SELECT MAX(\"{r['column_name']}\") FROM public.\"{r['table_name']}\"), 0) + 1, false)"
        )


async def snapshot_catalogue() -> None:
    config = load_config()
    tables: list[str] = [*config["snapshot_tables"], "alembic_version"]
    prod = await asyncpg.connect(prod_dsn(), statement_cache_size=0, timeout=30)
    local = await asyncpg.connect(local_dsn())
    try:
        await prod.execute("SET default_transaction_read_only = on")
        # Sin triggers ni comprobación de FKs durante la copia: se conservan
        # timestamps y contadores tal cual están en producción.
        await local.execute("SET session_replication_role = replica")

        admin_ids = [
            r["id"]
            for r in await local.fetch(
                "SELECT id FROM auth.users WHERE lower(email) = ANY($1::text[])",
                [e.lower() for e in config["admin_emails"]],
            )
        ]
        if admin_ids:
            await local.execute("DELETE FROM public.user_roles WHERE user_id = ANY($1::uuid[])", admin_ids)
            await local.execute("DELETE FROM public.profiles WHERE user_id = ANY($1::uuid[])", admin_ids)
            n_prof = await _copy_rows(prod, local, "profiles", "WHERE user_id = ANY($1::uuid[])", (admin_ids,))
            n_roles = await _copy_rows(prod, local, "user_roles", "WHERE user_id = ANY($1::uuid[])", (admin_ids,))
            print(f"  perfil de admin: {n_prof}, roles: {n_roles}")

        await local.execute("TRUNCATE " + ", ".join(f'public."{t}"' for t in tables) + " CASCADE")
        for table in tables:
            print(f"  {table}: {await _copy_rows(prod, local, table)} filas")
        await _fix_orphans(local, tables)
        await _reset_sequences(local, tables)
        await local.execute("SET session_replication_role = origin")
    finally:
        await prod.close()
        await local.close()


def alembic_upgrade_head() -> None:
    env = {**os.environ, "DATABASE_URL": local_sqlalchemy_url(), "APP_ENV": "local"}
    _run([sys.executable, "-m", "alembic", "upgrade", "head"], env=env, cwd=API_DIR)


async def main() -> None:
    print("→ Recreando base de datos local")
    await recreate_database()
    print("→ Restaurando el esquema real de producción (pg_dump, solo estructura)")
    await build_schema()
    write_state(db_created_at=utcnow().isoformat())
    print("→ Sincronizando usuarios de Auth permitidos")
    await auth_sync.sync_once(verbose=True)
    print("→ Copiando catálogo de producción (solo lectura)")
    await snapshot_catalogue()
    write_state(snapshot_at=utcnow().isoformat())
    print("→ Aplicando migraciones de la rama pendientes en producción (alembic upgrade head)")
    alembic_upgrade_head()
    print("✓ Base de datos local lista")


if __name__ == "__main__":
    asyncio.run(main())
