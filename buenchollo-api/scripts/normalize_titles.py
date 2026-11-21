"""Limpieza única de los títulos ya publicados (chollos y productos).

Aplica `app.modules.deals.domain.titles.normalize_title`, la misma regla que
se usa al publicar o editar. Los slugs (URLs) NO cambian. Imprime un informe
en Markdown con cada cambio (antes → después) y los títulos que conviene
revisar a mano (p. ej. los que solo dicen la marca).

Por defecto solo simula. Con `--apply` escribe en la BD en una única
transacción. Hacer antes una copia (`docker restart buenchollo-db-backup`).

Uso en producción, sin reconstruir la imagen (el script se envía por stdin):

    ssh -o BatchMode=yes nas-zambu \
      'sudo -n /volume1/@appstore/ContainerManager/usr/bin/docker exec -i buenchollo-api python - --apply' \
      < buenchollo-api/scripts/normalize_titles.py > informe-titulos.md

En local (desde buenchollo-api/): python scripts/normalize_titles.py [--apply]
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent) if "__file__" in globals() else "/app")

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.database import PGBOUNCER_CONNECT_ARGS  # noqa: E402
from app.modules.catalog.domain.models import Product  # noqa: E402
from app.modules.deals.domain.models import Deal  # noqa: E402
from app.modules.deals.domain.titles import needs_manual_review, normalize_title  # noqa: E402


def _md(text: str) -> str:
    return text.replace("|", "\\|")


async def main(apply: bool) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, poolclass=NullPool, connect_args=PGBOUNCER_CONNECT_ARGS)
    changes: list[tuple[str, str, str, str]] = []  # (tipo, slug, antes, después)
    manual: list[tuple[str, str, str]] = []
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            deals = (await session.execute(select(Deal).order_by(Deal.published_at.desc().nulls_last()))).scalars()
            for deal in deals:
                new = normalize_title(deal.title)
                if new != deal.title:
                    changes.append(("chollo", deal.slug, deal.title, new))
                    deal.title = new
                if needs_manual_review(new):
                    manual.append((deal.status, deal.slug, new))
            products = (await session.execute(select(Product).order_by(Product.slug))).scalars()
            for product in products:
                new = normalize_title(product.title)
                if new != product.title:
                    changes.append(("producto", product.slug, product.title, new))
                    product.title = new
            if apply:
                await session.commit()
            else:
                await session.rollback()
    finally:
        await engine.dispose()

    mode = "APLICADO" if apply else "SIMULACIÓN (sin cambios en la BD)"
    print(f"# Normalización de títulos · {mode}\n")
    print(f"{len(changes)} título(s) cambiado(s). Los slugs y URLs no cambian.\n")
    print("| Tipo | Slug | Antes | Después |\n|---|---|---|---|")
    for kind, slug, old, new in changes:
        print(f"| {kind} | `{slug}` | {_md(old)} | {_md(new)} |")
    print(f"\n## Revisar a mano ({len(manual)})\n")
    print("Títulos de una sola palabra (normalmente solo la marca): editarlos desde Admin → Chollos.\n")
    for status, slug, title in manual:
        print(f"- `{slug}` ({status}): {_md(title)}")


if __name__ == "__main__":
    asyncio.run(main(apply="--apply" in sys.argv[1:]))
