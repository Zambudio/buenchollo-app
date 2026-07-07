"""Alembic environment.

Configura el motor SQLAlchemy async desde `app.core.config`, registra todos
los modelos mediante `app.core.base` y aplica un filtro de objetos que evita
que Alembic genere drops de tablas externas (auth.users, storage.*) o de
tablas legacy gestionadas con SQL puro (user_roles, import_logs).
"""
import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Permite importar `app.*` desde alembic
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import get_settings  # noqa: E402
from app.core.base import Base  # noqa: E402 — registra todos los modelos

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Sobrescribir sqlalchemy.url desde .env / config en lugar del placeholder del .ini
settings = get_settings()
if settings.database_url:
    # Alembic almacena la url vía ConfigParser, que interpreta '%' como
    # sintaxis de interpolación (%(var)s). Si DATABASE_URL trae caracteres
    # URL-encoded en la contraseña (p.ej. %40 = '@', %E2%82%AC = '€'), hay
    # que escapar el '%' duplicándolo. No afecta al runtime de la app, que
    # pasa el URL directamente a asyncpg sin ConfigParser.
    config.set_main_option(
        "sqlalchemy.url",
        settings.database_url.replace("%", "%%"),
    )


# ── Filtros ─────────────────────────────────────────────────────────────────
# Tablas del schema `public` que NO están modeladas como SQLAlchemy ORM.
# Alembic las ignorará: sin esta lista, un --autogenerate generaría drops.
_LEGACY_TABLES_NOT_MODELED = {"user_roles", "import_logs"}


def include_object(obj, name, type_, reflected, compare_to):
    """Devuelve True si Alembic debe considerar este objeto.

    - Ignora cualquier tabla en schemas distintos a `public` (auth, storage,
      supabase_migrations, etc.).
    - Ignora las tablas legacy no modeladas (gestionadas con SQL en
      buenchollo-api/supabase/migrations/).
    """
    if type_ == "table":
        schema = getattr(obj, "schema", None)
        if schema and schema != "public":
            return False
        if name in _LEGACY_TABLES_NOT_MODELED:
            return False
    return True


# ── Modos online / offline ──────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (genera SQL sin conectar)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        include_schemas=False,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        include_schemas=False,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"server_settings": {"jit": "off"}, "statement_cache_size": 0},
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
