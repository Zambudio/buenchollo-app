"""Sincronización acotada de los feeds Awin seleccionados.

- Nunca se lanza desde una petición del editor: la invocan el panel (en
  segundo plano), el scheduler diario o `scripts/sync_awin_feeds.py`.
- Una sola descarga de la lista de feeds por ejecución; cada feed solo se
  descarga si su `Last Imported` ha cambiado desde la última sincronización.
- Descarga en streaming a un temporal con tope de tamaño; descompresión y
  número de filas también limitados; inserción por lotes.
- Escritura por generación: la nueva solo se activa si termina bien; un fallo
  borra la parcial y deja intacta la anterior.
"""

from __future__ import annotations

import asyncio
import logging
import random
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from app.modules.affiliates.domain.models import NETWORK_AWIN, AffiliateProgram
from app.modules.affiliates.infrastructure.awin_client import AwinClient, _parse_dt
from app.modules.affiliates.infrastructure.http import redact
from app.modules.affiliates.infrastructure.repository import AffiliateRepository

logger = logging.getLogger(__name__)

BATCH_SIZE = 1000


def merge_feed_metadata(program: AffiliateProgram, listed: list[dict]) -> list[dict]:
    """Actualiza los feeds conocidos del programa con la lista de Awin,
    conservando la selección y el estado de sincronización. Sin URLs."""
    known = {str(f.get("feed_id")): dict(f) for f in program.feeds or [] if f.get("feed_id")}
    for row in listed:
        if str(row.get("advertiser_id")) != str(program.advertiser_id):
            continue
        feed = known.setdefault(str(row["feed_id"]), {"feed_id": str(row["feed_id"]), "selected": False})
        feed.update(
            {
                "name": row.get("name"),
                "language": row.get("language"),
                "format": row.get("format"),
                "products": row.get("products"),
                "last_imported": row.get("last_imported"),
                "membership_status": row.get("membership_status"),
                "available": True,
            }
        )
    listed_ids = {str(r["feed_id"]) for r in listed if str(r.get("advertiser_id")) == str(program.advertiser_id)}
    for feed_id, feed in known.items():
        if feed_id not in listed_ids:
            feed["available"] = False
    return list(known.values())


class AwinFeedSync:
    def __init__(self, repo: AffiliateRepository, client: AwinClient) -> None:
        self.repo = repo
        self.client = client

    async def run(self, *, program_id: str | None = None, force: bool = False, jitter: bool = False) -> list[dict]:
        if not self.client.feeds_configured:
            return [{"status": "not_configured", "message": "Faltan AWIN_PUBLISHER_ID / AWIN_FEED_API_KEY."}]
        if jitter:  # recomendación de Awin: no lanzar en el segundo 0 de cada hora/minuto
            await asyncio.sleep(random.uniform(10, 120))
        programs = [
            p
            for p in await self.repo.list_programs()
            if p.network == NETWORK_AWIN and p.enabled and (program_id is None or p.id == program_id)
        ]
        if not programs:
            return []
        listed = await asyncio.to_thread(self.client.feed_list)
        urls = {str(r["feed_id"]): r.get("url") for r in listed}
        report = []
        for program in programs:
            program.feeds = merge_feed_metadata(program, listed)
            await self.repo.save(program)
            for feed in list(program.feeds):
                if not feed.get("selected"):
                    continue
                report.append(await self._sync_feed(program, feed, urls.get(str(feed["feed_id"])), force))
        return report

    async def _sync_feed(self, program: AffiliateProgram, feed: dict, url: str | None, force: bool) -> dict:
        feed_id = str(feed["feed_id"])
        program_id = program.id  # tras un rollback los atributos ORM quedan expirados
        base = {"program": program.name, "feed_id": feed_id}
        if not url or not feed.get("available"):
            await self._update_feed(program, feed_id, last_status="unavailable", last_error="El feed ya no figura en la lista de Awin.")
            return {**base, "status": "unavailable"}
        if not force and feed.get("generation") is not None and feed.get("last_synced_remote") == feed.get("last_imported"):
            return {**base, "status": "unchanged"}

        generation = int(datetime.now(timezone.utc).timestamp() * 1000)
        feed_updated = _parse_dt(feed.get("last_imported"))
        rows_total = 0
        try:
            with tempfile.TemporaryDirectory(prefix="bct-awin-") as tmp:
                path = Path(tmp) / "feed.bin"
                await asyncio.to_thread(self.client.download_feed, url, path)
                rows_total = await self._load(program, feed_id, generation, path, feed_updated)
            await self.repo.delete_generation(program.id, feed_id, keep=generation)
            await self._update_feed(
                program,
                feed_id,
                generation=generation,
                last_synced_remote=feed.get("last_imported"),
                last_synced_at=datetime.now(timezone.utc).isoformat(),
                last_status="ok",
                last_error=None,
                rows=rows_total,
            )
            return {**base, "status": "ok", "rows": rows_total}
        except Exception as exc:  # cualquier fallo: conservar la generación anterior
            await self.repo.session.rollback()
            await self.repo.delete_generation(program_id, feed_id, only=generation)
            await self.repo.session.commit()
            message = redact(str(exc), self.client.secrets) or exc.__class__.__name__
            logger.warning("Sincronización del feed Awin %s fallida: %s", feed_id, message)
            program = await self.repo.get_program(program_id) or program
            await self._update_feed(
                program,
                feed_id,
                last_status="error",
                last_error=message,
                last_synced_at=datetime.now(timezone.utc).isoformat(),
            )
            return {**base, "status": "error", "message": message}

    async def _load(self, program, feed_id: str, generation: int, path: Path, feed_updated) -> int:
        imported_at = datetime.now(timezone.utc)
        seen: set[str] = set()
        total = 0
        iterator = iter(self.client.iter_feed_file(path))
        while True:
            # Lectura/descompresión en un hilo, por lotes (no bloquea el event loop).
            chunk = await asyncio.to_thread(_take, iterator, BATCH_SIZE)
            if not chunk:
                break
            batch = []
            for row in chunk:
                if row["product_key"] in seen:
                    continue
                seen.add(row["product_key"])
                row.update(
                    {
                        "program_id": program.id,
                        "feed_id": feed_id,
                        "generation": generation,
                        "imported_at": imported_at,
                        "provider_updated_at": row.get("provider_updated_at") or feed_updated,
                    }
                )
                batch.append(row)
            await self.repo.insert_feed_rows(batch)
            await self.repo.session.commit()
            total += len(batch)
        return total

    async def _update_feed(self, program: AffiliateProgram, feed_id: str, **changes) -> None:
        feeds = []
        for feed in program.feeds or []:
            feed = dict(feed)
            if str(feed.get("feed_id")) == feed_id:
                feed.update(changes)
            feeds.append(feed)
        program.feeds = feeds  # reasignar: SQLAlchemy no detecta mutaciones de JSON
        await self.repo.save(program)


def _take(iterator, n: int) -> list[dict]:
    out = []
    for row in iterator:
        out.append(row)
        if len(out) >= n:
            break
    return out
