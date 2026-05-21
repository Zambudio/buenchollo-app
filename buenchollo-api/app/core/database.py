"""Database connection and session management using SQLAlchemy."""

from typing import AsyncGenerator
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Avoid creating the engine if no database URL is provided (e.g. during simple tests)
engine = None
AsyncSessionLocal = None

if settings.database_url:
    try:
        engine = create_async_engine(
            settings.database_url,
            echo=settings.log_level == "DEBUG",
            future=True,
            pool_pre_ping=True, # Verifica si la conexión sigue viva
            connect_args={"server_settings": {"jit": "off"}, "statement_cache_size": 0},
        )
        AsyncSessionLocal = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )
        logger.info("Motor de base de datos SQLAlchemy (Async) inicializado.")
    except Exception as e:
        logger.error(f"Error al inicializar el motor de base de datos: {e}")
else:
    logger.warning("DATABASE_URL no configurada. SQLAlchemy no se inicializará.")

# Base para los modelos
Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency que inyecta una sesión de BD asíncrona por request."""
    if AsyncSessionLocal is None:
        raise Exception("Database engine not initialized (DATABASE_URL missing)")
        
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
