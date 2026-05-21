"""Service to automatically clean up old expired deals."""

import logging
from datetime import datetime, timedelta
from supabase import create_client
from app.core.config import Settings

logger = logging.getLogger(__name__)

class DealCleanerService:
    """Service to delete deals that have been expired for more than 5 days."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = None

    @property
    def client(self):
        """Lazy initialization of the Supabase client with safety checks."""
        if self._client is None:
            if not self.settings.supabase_url or not self.settings.supabase_key:
                logger.error("Faltan credenciales de Supabase para la limpieza automática.")
                return None
            self._client = create_client(self.settings.supabase_url, self.settings.supabase_key)
        return self._client

    def clean_expired_deals(self) -> int:
        """
        Delete deals where expires_at is older than 5 days from now.
        Returns the number of deleted deals.
        """
        try:
            # Calculate the threshold date (5 days ago)
            threshold = (datetime.now() - timedelta(days=5)).isoformat()
            
            logger.info("Iniciando limpieza de chollos caducados antes de: %s", threshold)
            
            # Supabase delete with filter
            response = self.client.table("deals").delete().lt("expires_at", threshold).execute()
            
            count = len(response.data) if response.data else 0
            logger.info("Limpieza completada. Chollos borrados: %d", count)
            return count
            
        except Exception as exc:
            logger.error("Error durante la limpieza de chollos: %s", exc)
            return 0
