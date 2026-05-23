"""Repositorio de categorías Telegram almacenadas en un fichero JSON local."""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Ruta por defecto: <raíz del proyecto>/data/categories.json
# buenchollo-api/app/modules/telegram/infrastructure/ → 4 niveles arriba = buenchollo-api/
_DEFAULT_PATH = Path(__file__).resolve().parents[4] / "data" / "categories.json"


class JsonCategoryRepository:
    """Lee y escribe el catálogo de categorías Telegram desde/hacia un archivo JSON."""

    def __init__(self, path: Path | str | None = None) -> None:
        self._path = Path(path) if path else _DEFAULT_PATH

    def load(self) -> list[str]:
        """Devuelve la lista de categorías ordenada alfabéticamente."""
        if not self._path.exists():
            logger.warning("categories.json no encontrado en %s", self._path)
            return []
        try:
            with self._path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return sorted(data.get("categories", []))
        except Exception as exc:
            logger.error("Error leyendo categories.json: %s", exc)
            return []

    def add(self, category: str) -> list[str]:
        """
        Añade una nueva categoría al catálogo si no existe ya.
        Escribe de forma atómica (tmp + rename) para no perder datos.
        Devuelve la lista actualizada.
        """
        cats = self.load()
        normalized = category.strip()
        if not normalized.startswith("#"):
            normalized = f"#{normalized}"

        if normalized in cats:
            return sorted(cats)

        cats.append(normalized)
        cats_sorted = sorted(cats)

        payload = {
            "version": 1,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "categories": cats_sorted,
        }

        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        try:
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self._path)
        except Exception as exc:
            logger.error("Error escribiendo categories.json: %s", exc)
            tmp.unlink(missing_ok=True)
            raise

        return cats_sorted
