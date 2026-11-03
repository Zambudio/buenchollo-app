"""Rellena `deals.canonical_url` para los chollos existentes.

Uso (desde buenchollo-api/):

    python scripts/backfill_canonical_urls.py            # dry-run (por defecto)
    python scripts/backfill_canonical_urls.py --apply    # escribe en la BD

Idempotente: solo toca deals con `canonical_url IS NULL`. Los que no producen
una URL canonica valida se cuentan como omitidos y no se vuelven a procesar
en la misma ejecucion.
"""
import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=True)

from sqlalchemy import select, update  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.modules.affiliates.domain.links import InvalidLinkError, canonicalize  # noqa: E402
import app.modules.categories.domain.models  # noqa: E402,F401
import app.modules.stores.domain.models  # noqa: E402,F401
import app.modules.users.domain.models  # noqa: E402,F401
from app.modules.deals.domain.models import Deal  # noqa: E402

BATCH_SIZE = 200


def compute_canonical(affiliate_url: str | None, external_id: str | None) -> str | None:
    if not affiliate_url:
        return None
    try:
        link = canonicalize(affiliate_url, asin=external_id)
    except InvalidLinkError:
        return None
    return link.canonical_url if link.host else None


async def run(apply: bool) -> dict[str, int]:
    updated = skipped = 0
    last_id: str | None = None
    while True:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Deal.id, Deal.affiliate_url, Deal.external_id)
                .where(Deal.canonical_url.is_(None))
                .order_by(Deal.id)
                .limit(BATCH_SIZE)
            )
            if last_id is not None:
                stmt = stmt.where(Deal.id > last_id)
            rows = (await session.execute(stmt)).all()
            if not rows:
                break
            for deal_id, affiliate_url, external_id in rows:
                canonical = compute_canonical(affiliate_url, external_id)
                if canonical is None:
                    skipped += 1
                    continue
                updated += 1
                if apply:
                    await session.execute(
                        update(Deal).where(Deal.id == deal_id).values(canonical_url=canonical, updated_at=Deal.updated_at)
                    )
            if apply:
                await session.commit()
            last_id = rows[-1][0]
    return {"updated": updated, "skipped": skipped}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="escribe los cambios (por defecto solo simula)")
    args = parser.parse_args()
    result = asyncio.run(run(args.apply))
    mode = "APLICADO" if args.apply else "DRY-RUN"
    print(f"[{mode}] actualizables/actualizados={result['updated']} omitidos={result['skipped']}")


if __name__ == "__main__":
    main()
