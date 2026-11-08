"""Sincroniza los feeds Awin seleccionados (mismo código que el job diario).

Uso (desde buenchollo-api/):

    python scripts/sync_awin_feeds.py                 # solo feeds cambiados
    python scripts/sync_awin_feeds.py --force         # descarga aunque no hayan cambiado
    python scripts/sync_awin_feeds.py --program <id>  # un programa concreto

Necesita DATABASE_URL, AWIN_PUBLISHER_ID y AWIN_FEED_API_KEY. Imprime un
resumen sin URLs ni claves.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings  # noqa: E402
from app.modules.affiliates.application.feed_sync_job import run_awin_feed_sync_async  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--program")
    args = parser.parse_args()
    report = asyncio.run(run_awin_feed_sync_async(get_settings(), program_id=args.program, force=args.force))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if any(r.get("status") == "error" for r in report) else 0


if __name__ == "__main__":
    raise SystemExit(main())
