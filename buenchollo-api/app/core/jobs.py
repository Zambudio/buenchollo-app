"""Conexión a BD de los jobs de fondo (contenedor `scheduler`, BackgroundTasks, CLI).

Cada job corre en su propio event loop (`asyncio.run`), así que no puede usar
el pool del web (`core/database.py`), atado al loop de uvicorn: abre un engine
con NullPool (una conexión por uso, sin conexiones ociosas contra PgBouncer)
y lo libera al terminar.
"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.core.database import PGBOUNCER_CONNECT_ARGS


@asynccontextmanager
async def job_engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
        connect_args=PGBOUNCER_CONNECT_ARGS,
    )
    try:
        yield engine
    finally:
        await engine.dispose()


@asynccontextmanager
async def job_session(settings: Settings) -> AsyncIterator[AsyncSession]:
    async with job_engine(settings) as engine:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            yield session
