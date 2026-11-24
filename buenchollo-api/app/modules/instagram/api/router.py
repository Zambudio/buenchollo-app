from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import require_admin
from app.modules.instagram.infrastructure.repository import InstagramRepository

router = APIRouter(prefix="/instagram", tags=["instagram"])

# Una imagen solo se sirve mientras su publicación está pendiente y es reciente.
MEDIA_TTL = timedelta(hours=48)


@router.get("/media/{post_id}.jpg", include_in_schema=False)
@limiter.limit("60/minute")
async def instagram_media(request: Request, post_id: UUID, db: AsyncSession = Depends(get_db)) -> Response:
    """Imagen de una publicación pendiente, para que Instagram la descargue.

    Pública (Instagram no manda credenciales): la protege el id aleatorio
    (uuid4) y que deja de servirse al publicarse o a las 48 h."""
    image = await InstagramRepository(db).pending_image(str(post_id), datetime.now(timezone.utc) - MEDIA_TTL)
    if not image:
        raise HTTPException(status_code=404)
    return Response(
        content=image,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex"},
    )


@router.get("/status")
async def instagram_status(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_user=Depends(require_admin),
) -> dict:
    """Estado de la conexión y de la cola (sin el token)."""
    repo = InstagramRepository(db)
    account = await repo.account()
    return {
        "enabled": settings.instagram_enabled,
        "token_configured": bool(settings.instagram_access_token),
        "connected": bool(account and account.user_id),
        "username": account.username if account else None,
        "token_refreshed_at": account.refreshed_at if account else None,
        "token_expires_at": account.expires_at if account else None,
        "last_error": account.last_error if account else None,
        "queue": await repo.counts(),
        "recent": [
            {
                "id": p.id,
                "status": p.status,
                "attempts": p.attempts,
                "title": p.caption.split("\n", 1)[0][:120],
                "media_id": p.media_id,
                "last_error": p.last_error,
                "created_at": p.created_at,
                "published_at": p.published_at,
            }
            for p in await repo.recent()
        ],
    }
