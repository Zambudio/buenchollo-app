"""Estado de las redes de afiliación, solo lectura (no escribe en la BD).

Muestra, para cada programa del registro `affiliate_programs`:
- lo que dice la red ahora (Awin: relación del programa; Tradedoubler: feeds
  accesibles al token);
- lo que tiene guardado la BD (habilitado, adhesión, tienda, feeds
  seleccionados, permisos de imagen);
- los feeds de producto que la red ofrece para ese anunciante.

Pensado para que un agente compruebe si ya hay tiendas aprobadas antes de
guiar la activación (docs/guides/AFFILIATE-ACTIVATION-RUNBOOK.md). Nunca
imprime claves, tokens ni URLs de descarga.

Uso en producción, sin reconstruir la imagen (el script se envía por stdin):

    ssh -o BatchMode=yes nas-zambu \
      'sudo -n /volume1/@appstore/ContainerManager/usr/bin/docker exec -i buenchollo-api python -' \
      < buenchollo-api/scripts/check_affiliate_status.py

En local (desde buenchollo-api/): python scripts/check_affiliate_status.py
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent) if "__file__" in globals() else "/app")

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.modules.affiliates.domain.models import AffiliateProgram  # noqa: E402
from app.modules.affiliates.infrastructure.awin_client import AwinClient  # noqa: E402
from app.modules.affiliates.infrastructure.tradedoubler_client import TradedoublerClient  # noqa: E402


async def _programs(settings) -> list[AffiliateProgram]:
    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
        connect_args={"server_settings": {"jit": "off"}, "statement_cache_size": 0},
    )
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            rows = await session.execute(select(AffiliateProgram).order_by(AffiliateProgram.network, AffiliateProgram.name))
            return list(rows.scalars().all())
    finally:
        await engine.dispose()


def _safe(fn, *args):
    try:
        return fn(*args), None
    except Exception as exc:  # noqa: BLE001 - informe, no fallo
        return None, f"{type(exc).__name__}: {str(exc)[:200]}"


def main() -> int:
    settings = get_settings()
    awin, td = AwinClient(settings), TradedoublerClient(settings)
    out: dict = {
        "credentials": {
            "awin_publisher_api": awin.api_configured,
            "awin_feeds": awin.feeds_configured,
            "tradedoubler_products": td.configured,
            "tradedoubler_site_id": bool(settings.tradedoubler_site_id),
        },
        "programs": [],
    }
    try:
        relations, awin_rel_err = _safe(awin.programmes_by_relationship, "ES") if awin.api_configured else ({}, "sin credenciales")
        awin_feeds, awin_feed_err = _safe(awin.feed_list) if awin.feeds_configured else ([], "sin credenciales")
        td_feeds, td_err = _safe(td.product_feeds) if td.configured else ([], "sin credenciales")
    finally:
        awin.http.close()
        td.http.close()
    out["errors"] = {k: v for k, v in {"awin_programmes": awin_rel_err, "awin_feeds": awin_feed_err, "tradedoubler_feeds": td_err}.items() if v}

    for p in asyncio.run(_programs(settings)):
        adv = str(p.advertiser_id)
        if p.network == "awin":
            live = (relations or {}).get(adv, "notjoined") if relations is not None else None
            offered = [
                {"feed_id": f["feed_id"], "name": f["name"], "language": f["language"], "products": f["products"],
                 "last_imported": f["last_imported"], "membership": f["membership_status"]}
                for f in (awin_feeds or []) if str(f.get("advertiser_id")) == adv
            ]
        else:
            mine = [f for f in (td_feeds or []) if adv in f["program_ids"]]
            live = ("joined (feeds accesibles)" if mine else "sin feeds accesibles") if td_feeds is not None else None
            offered = [{k: f[k] for k in ("feed_id", "name", "language", "products", "last_imported")} for f in mine]
        out["programs"].append(
            {
                "network": p.network,
                "advertiser_id": adv,
                "name": p.name,
                "live_membership": live,
                "db": {
                    "enabled": p.enabled,
                    "membership_status": p.membership_status,
                    "membership_source": p.membership_source,
                    "store_linked": bool(p.store_id),
                    "domains": p.domains,
                    "image_channels": (p.restrictions or {}).get("image_channels", []),
                    "selected_feeds": [f.get("feed_id") for f in p.feeds or [] if f.get("selected")],
                    "feed_sync": [
                        {k: f.get(k) for k in ("feed_id", "last_status", "rows", "last_synced_at", "last_error") if f.get(k) is not None}
                        for f in p.feeds or [] if f.get("selected")
                    ],
                    "deeplink_verified": bool(p.deeplink_verified_at),
                },
                "feeds_offered": offered,
            }
        )
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
