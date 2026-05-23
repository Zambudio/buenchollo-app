from fastapi import APIRouter, Depends, HTTPException
from app.core.config import get_settings
from app.core.security import require_admin
from app.modules.telegram.infrastructure.telegram_bot import TelegramBot
from app.modules.telegram.api.schemas import TelegramNotifyRequest

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/notify")
async def notify_deal(
    payload: TelegramNotifyRequest,
    _auth=Depends(require_admin),
) -> dict:
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise HTTPException(
            status_code=503,
            detail="Telegram no configurado. Añade TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID al .env",
        )
    bot = TelegramBot(settings.telegram_bot_token, settings.telegram_chat_id)
    ok = bot.send_deal(
        title=payload.title,
        current_price=payload.current_price,
        previous_price=payload.previous_price,
        discount_percentage=payload.discount_percentage,
        short_description=payload.short_description,
        image_url=payload.image_url,
        affiliate_url=payload.affiliate_url,
        public_url=payload.public_url,
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Error al enviar a Telegram. Revisa los logs del servidor.")
    return {"ok": True}
