"""Crea el esquema de test desde los modelos ORM (CI de integración, TD-07).

El esquema real de producción es mixto: las tablas base las crearon las
migraciones SQL de Supabase (dependen de `auth.*` y RLS, irreproducibles en
un Postgres vanilla) y Alembic solo versiona cambios incrementales. Para el
CI basta con el grafo ORM completo: es exactamente la superficie que
ejercitan los repositorios en los tests de integración.

Uso (desde buenchollo-api/, con DATABASE_URL apuntando al Postgres de test):

    python scripts/create_test_schema.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Registrar el grafo completo de modelos antes de create_all (mismo orden
# que conftest.py: los relationship() se resuelven por nombre).
import app.modules.users.domain.models  # noqa: F401, E402
import app.modules.categories.domain.models  # noqa: F401, E402
import app.modules.stores.domain.models  # noqa: F401, E402
import app.modules.deals.domain.models  # noqa: F401, E402
import app.modules.alerts.domain.models  # noqa: F401, E402
import app.modules.notifications.domain.models  # noqa: F401, E402
import app.modules.comments.domain.models  # noqa: F401, E402
import app.core.audit.models  # noqa: F401, E402

from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.database import Base  # noqa: E402


async def main() -> None:
    settings = get_settings()
    if not settings.database_url:
        raise SystemExit("DATABASE_URL no configurada")
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print(f"Esquema creado: {len(Base.metadata.tables)} tablas")


if __name__ == "__main__":
    asyncio.run(main())
