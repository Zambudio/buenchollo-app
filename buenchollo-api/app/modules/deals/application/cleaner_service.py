"""Mantenimiento automático de deals: caducidad por fecha y activación programada.

Catálogo permanente: aquí ya no se borra ningún chollo. La caducidad solo
cambia el estado; la revisión diaria de precios (`price_check`) decide el
resto del ciclo de vida.
"""

import logging
from datetime import datetime, timezone
from typing import Callable, TypeVar
from supabase import create_client
from app.core.config import Settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


class DealCleanerService:
    """Caducidad por fecha y activación de deals programados."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not self.settings.supabase_url or not self.settings.supabase_key:
                logger.error("Faltan credenciales de Supabase para el scheduler.")
                return None
            self._client = create_client(self.settings.supabase_url, self.settings.supabase_key)
        return self._client

    def _safe_run(self, action_name: str, action: Callable[[], T], default: T) -> T:
        """Ejecuta `action` capturando cualquier excepción y devolviendo `default`.
        Centraliza el patrón try/except/log que repetía cada tarea del scheduler."""
        try:
            return action()
        except Exception as exc:
            logger.error("Error en %s: %s", action_name, exc)
            return default

    @staticmethod
    def _count_response_rows(response) -> int:
        return len(response.data) if response.data else 0

    def mark_expired_deals(self) -> int:
        """Marca como 'expired' los deals activos cuyo expires_at ya ha pasado."""
        def _action() -> int:
            now = datetime.now(timezone.utc).isoformat()
            response = (
                self.client.table("deals")
                .update({"status": "expired", "offer_end_reason": "expired_date"})
                .eq("status", "active")
                .lt("expires_at", now)
                .execute()
            )
            count = self._count_response_rows(response)
            if count:
                logger.info("Scheduler: %d chollo(s) marcado(s) como expired", count)
            return count

        return self._safe_run("marcar chollos caducados", _action, default=0)

    def activate_scheduled_deals(self) -> int:
        """Activa los chollos con status='scheduled' cuyo scheduled_for ya ha llegado."""
        def _action() -> int:
            now = datetime.now(timezone.utc).isoformat()
            response = (
                self.client.table("deals")
                .update({"status": "active", "published_at": now})
                .eq("status", "scheduled")
                .lte("scheduled_for", now)
                .execute()
            )
            count = self._count_response_rows(response)
            if count:
                logger.info("Scheduler: %d chollo(s) activado(s)", count)
            return count

        return self._safe_run("activar chollos programados", _action, default=0)
