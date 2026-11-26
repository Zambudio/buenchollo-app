import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import require_admin
from app.modules.whatsapp.infrastructure.gateway_client import GatewayError, WhatsAppGatewayClient
from app.modules.whatsapp.infrastructure.repository import WhatsAppRepository

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.get("/status")
async def whatsapp_status(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_user=Depends(require_admin),
) -> dict:
    """Estado de la pasarela y de la cola del Canal de WhatsApp (sin el token)."""
    gateway: dict = {"reachable": False}
    if settings.whatsapp_gateway_token:
        client = WhatsAppGatewayClient(settings.whatsapp_gateway_url, settings.whatsapp_gateway_token)
        try:
            status = await asyncio.to_thread(client.status)
            gateway = {
                "reachable": True,
                "connection": status.connection,
                "me": status.me,
                "pairing_code": status.pairing_code,
                "last_error": status.last_error,
            }
        except GatewayError as exc:
            gateway["error"] = str(exc)
    repo = WhatsAppRepository(db)
    return {
        "enabled": settings.whatsapp_enabled,
        "channel_configured": bool(settings.whatsapp_channel),
        "channels": settings.whatsapp_channels,
        "min_interval_minutes": settings.whatsapp_min_interval_minutes,
        "daily_limit": settings.whatsapp_daily_limit,
        "gateway": gateway,
        "queue": await repo.counts(),
        "recent": [
            {
                "id": p.id,
                "status": p.status,
                "attempts": p.attempts,
                "title": p.text.split("\n", 1)[0].replace("*", "")[:120],
                "has_image": p.image is not None,
                "message_id": p.message_id,
                "last_error": p.last_error,
                "created_at": p.created_at,
                "not_before": p.not_before,
                "published_at": p.published_at,
            }
            for p in await repo.recent()
        ],
    }
