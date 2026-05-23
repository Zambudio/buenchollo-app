"""Servicios de mantenimiento automático de deals (limpieza y activación programada)."""

import logging
from datetime import datetime, timedelta, timezone
from supabase import create_client
from app.core.config import Settings

logger = logging.getLogger(__name__)


class DealCleanerService:
    """Limpieza de deals caducados y activación de deals programados."""

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

    def clean_expired_deals(self) -> int:
        """Elimina deals con expires_at hace más de 2 días. Devuelve el número borrado."""
        try:
            threshold = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
            logger.info("Limpieza de chollos caducados antes de: %s", threshold)
            response = self.client.table("deals").delete().lt("expires_at", threshold).execute()
            count = len(response.data) if response.data else 0
            logger.info("Limpieza completada. Chollos borrados: %d", count)
            return count
        except Exception as exc:
            logger.error("Error durante la limpieza de chollos: %s", exc)
            return 0

    def mark_expired_deals(self) -> int:
        """Marca como 'expired' los deals activos cuyo expires_at ya ha pasado."""
        try:
            now = datetime.now(timezone.utc).isoformat()
            response = (
                self.client.table("deals")
                .update({"status": "expired"})
                .eq("status", "active")
                .lt("expires_at", now)
                .execute()
            )
            count = len(response.data) if response.data else 0
            if count:
                logger.info("Scheduler: %d chollo(s) marcado(s) como expired", count)
            return count
        except Exception as exc:
            logger.error("Error al marcar chollos caducados: %s", exc)
            return 0

    def activate_scheduled_deals(self) -> int:
        """Activa los chollos con status='scheduled' cuyo scheduled_for ya ha llegado."""
        try:
            now = datetime.now(timezone.utc).isoformat()
            response = (
                self.client.table("deals")
                .update({"status": "active", "published_at": now})
                .eq("status", "scheduled")
                .lte("scheduled_for", now)
                .execute()
            )
            count = len(response.data) if response.data else 0
            if count:
                logger.info("Scheduler: %d chollo(s) activado(s)", count)
            return count
        except Exception as exc:
            logger.error("Error al activar chollos programados: %s", exc)
            return 0
