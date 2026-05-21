"""Supabase client for fetching categories and subcategories."""

import logging
from typing import Any
from supabase import create_client
from app.core.config import Settings

logger = logging.getLogger(__name__)

class SupabaseCategoryClient:
    """Client to fetch category hierarchy from Supabase."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = None

    @property
    def client(self):
        """Lazy initialization of the Supabase client."""
        if self._client is None:
            url = self.settings.supabase_url
            if not url or not self.settings.supabase_key:
                raise ValueError("Faltan credenciales de Supabase en la configuración.")
            
            # Limpiar URL si trae /rest/v1/
            url = url.split("/rest/v1")[0].rstrip("/")
            self._client = create_client(url, self.settings.supabase_key)
        return self._client

    def get_categories_hierarchy(self) -> list[dict[str, Any]]:
        """Fetch all active categories and subcategories."""
        try:
            # Fetch all active categories
            response = self.client.table("categories").select("id, name, parent_id").eq("is_active", True).execute()
            return response.data or []
        except Exception as exc:
            logger.error("Error al obtener categorías de Supabase: %s", exc)
            return []

    def format_categories_for_prompt(self, categories: list[dict[str, Any]]) -> str:
        """Format the category list into a readable string for the LLM prompt."""
        parents = [c for c in categories if c.get("parent_id") is None]
        children = [c for c in categories if c.get("parent_id") is not None]
        
        lines = []
        for p in parents:
            lines.append(f"- {p['name']} (ID: {p['id']})")
            p_children = [c for c in children if c['parent_id'] == p['id']]
            for c in p_children:
                lines.append(f"  * {c['name']} (ID: {c['id']})")
        
        return "\n".join(lines)
