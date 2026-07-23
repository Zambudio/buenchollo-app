"""Job de publicación programada de artículos, ejecutado desde el
contenedor dedicado `buenchollo-scheduler` (no dentro de los workers de
FastAPI — mismo motivo que `scheduled_deals`: evitar publicar N veces si
uvicorn corre con --workers N).

Sigue el mismo patrón que
`app/modules/scheduled_deals/application/publication_worker.py`: un
wrapper síncrono (`run_due_scheduled_posts`) que abre su propio engine/
sesión y ejecuta el trabajo async con `asyncio.run`, para poder
registrarse como job de `BackgroundScheduler` (síncrono).
"""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.modules.blog.infrastructure.repository import BlogPostRepository

logger = logging.getLogger(__name__)


async def _publish_due_posts(repo: BlogPostRepository) -> int:
    """Publica los artículos programados vencidos. Cada uno se persiste en su
    propio SAVEPOINT (cuando la sesión lo soporta) para que un fallo puntual
    no envenene la sesión ni impida procesar el resto (§10: continuar si uno
    falla, sin publicar dos veces)."""
    due = await repo.get_due_scheduled()
    published = 0
    now = datetime.now(timezone.utc)
    session = getattr(repo, "session", None)
    for post in due:
        try:
            if session is not None:
                async with session.begin_nested():
                    _mark_published(post, now)
                    await repo.update(post)
            else:
                _mark_published(post, now)
                await repo.update(post)
            published += 1
        except Exception:
            logger.exception("Error publicando artículo programado id=%s", post.id)
    return published


def _mark_published(post, now: datetime) -> None:
    post.status = "published"
    post.published_at = post.published_at or now
    post.scheduled_for = None


async def _run(settings: Settings) -> int:
    if not settings.database_url:
        logger.error("DATABASE_URL no configurada para el worker de publicación de blog")
        return 0
    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
        connect_args={"server_settings": {"jit": "off"}, "statement_cache_size": 0},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            try:
                repo = BlogPostRepository(session)
                count = await _publish_due_posts(repo)
                await session.commit()
                if count:
                    logger.info("Worker de blog publicó %d artículo(s) programado(s)", count)
                return count
            except Exception:
                await session.rollback()
                logger.exception("Fallo global del worker de publicación programada de blog")
                return 0
    finally:
        await engine.dispose()


def run_due_scheduled_posts(settings: Settings) -> int:
    return asyncio.run(_run(settings))
