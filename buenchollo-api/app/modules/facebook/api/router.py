import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import require_admin
from app.modules.facebook.infrastructure.graph_client import FacebookApiError, FacebookGraphClient
from app.modules.facebook.infrastructure.repository import FacebookRepository

router = APIRouter(prefix="/facebook", tags=["facebook"])


@router.get("/status")
async def facebook_status(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_user=Depends(require_admin),
) -> dict:
    """Estado de la conexión con la página y de la cola (sin el token)."""
    page: dict = {"connected": False, "name": None, "error": None}
    token, page_id = (settings.facebook_access_token or "").strip(), (settings.facebook_page_id or "").strip()
    if token and page_id:
        try:
            access = await asyncio.to_thread(
                FacebookGraphClient(token, settings.facebook_graph_version).page_access, page_id
            )
            page = {"connected": True, "name": access.name, "error": None}
        except FacebookApiError as exc:
            page["error"] = str(exc)
    repo = FacebookRepository(db)
    return {
        "enabled": settings.facebook_enabled,
        "token_configured": bool(token),
        "page_id": page_id or None,
        "page": page,
        "queue": await repo.counts(),
        "recent": [
            {
                "id": p.id,
                "status": p.status,
                "attempts": p.attempts,
                "title": p.message.split("\n", 1)[0][:120],
                "post_id": p.post_id,
                "last_error": p.last_error,
                "created_at": p.created_at,
                "published_at": p.published_at,
            }
            for p in await repo.recent()
        ],
    }
