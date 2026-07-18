from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_log
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import require_admin
from app.modules.telegram.application.post_generator import TelegramPostGenerator
from app.modules.telegram.domain.exceptions import (
    TelegramChannelNotConfigured,
    TelegramNotConfigured,
    TelegramNotifyPayloadInvalid,
    TelegramSendFailed,
)
from app.modules.telegram.infrastructure.category_repository import JsonCategoryRepository
from app.modules.telegram.infrastructure.telegram_bot import TelegramBot
from app.modules.telegram.api.schemas import (
    TelegramCategoryAddRequest,
    TelegramCategoriesResponse,
    TelegramChannel,
    TelegramGenerateRequest,
    TelegramGenerateResponse,
    TelegramNotifyRequest,
)

router = APIRouter(prefix="/telegram", tags=["telegram"])


def _require_telegram(settings: Settings) -> None:
    if not settings.telegram_bot_token:
        raise TelegramNotConfigured()


def _get_bot(settings: Settings) -> TelegramBot:
    _require_telegram(settings)
    return TelegramBot(settings.telegram_bot_token)


def _get_category_repo() -> JsonCategoryRepository:
    return JsonCategoryRepository()


# ── Canales ────────────────────────────────────────────────────────────────────

@router.get("/channels", response_model=list[TelegramChannel])
async def get_channels(
    settings: Settings = Depends(get_settings),
    _auth=Depends(require_admin),
) -> list[TelegramChannel]:
    """Devuelve los canales disponibles configurados en el .env."""
    channels = []
    if settings.telegram_admin_channel_id:
        channels.append(TelegramChannel(id=settings.telegram_admin_channel_id, name="Canal Admin"))
    if settings.telegram_main_channel_id:
        channels.append(TelegramChannel(id=settings.telegram_main_channel_id, name="Canal General"))
    return channels


# ── Categorías ─────────────────────────────────────────────────────────────────

@router.get("/categories", response_model=TelegramCategoriesResponse)
async def get_categories(
    _auth=Depends(require_admin),
    repo: JsonCategoryRepository = Depends(_get_category_repo),
) -> TelegramCategoriesResponse:
    return TelegramCategoriesResponse(categories=repo.load())


@router.post("/categories", response_model=TelegramCategoriesResponse)
async def add_category(
    payload: TelegramCategoryAddRequest,
    _auth=Depends(require_admin),
    repo: JsonCategoryRepository = Depends(_get_category_repo),
) -> TelegramCategoriesResponse:
    updated = repo.add(payload.category)
    return TelegramCategoriesResponse(categories=updated)


# ── Generación de post ─────────────────────────────────────────────────────────

@router.post("/generate", response_model=TelegramGenerateResponse)
async def generate_post(
    payload: TelegramGenerateRequest,
    settings: Settings = Depends(get_settings),
    _auth=Depends(require_admin),
    repo: JsonCategoryRepository = Depends(_get_category_repo),
) -> TelegramGenerateResponse:
    """
    Genera el texto formateado del post y sugiere categorías vía GPT.
    La llamada a OpenAI es opcional: si falla o no hay clave, devuelve lista vacía.
    """
    generator = TelegramPostGenerator(openai_api_key=settings.openai_api_key)

    text = generator.generate_text(
        title=payload.title,
        current_price=payload.current_price,
        previous_price=payload.previous_price,
        discount_pct=payload.discount_percentage,
        description=payload.description,
        affiliate_url=payload.affiliate_url,
        expires_at=payload.expires_at,
    )

    categories = repo.load()
    suggested = await generator.suggest_categories(
        title=payload.title,
        description=payload.description or "",
        available=categories,
    )

    return TelegramGenerateResponse(text=text, suggested_categories=suggested)


# ── Publicación ────────────────────────────────────────────────────────────────

@router.post("/notify")
@limiter.limit("5/minute")  # publicación admin: evita doble envío accidental
async def notify_deal(
    request: Request,
    payload: TelegramNotifyRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_user=Depends(require_admin),
) -> dict:
    """
    Publica en Telegram.
    - Si payload.text está presente → usa send_preformatted (flujo del panel)
    - Si no → construye el mensaje en MarkdownV2 (flujo rápido del checkbox)
    """
    bot = _get_bot(settings)

    # Resuelve el canal destino
    channel_id = (
        payload.channel_id
        or settings.telegram_main_channel_id
    )
    if not channel_id:
        raise TelegramChannelNotConfigured()

    # Flujo panel: texto pre-formateado con custom entities
    if payload.text:
        generator = TelegramPostGenerator()
        entities = payload.entities or generator.build_entities(payload.text)
        ok = bot.send_preformatted(
            text=payload.text,
            entities=entities,
            image_url=payload.image_url,
            chat_id=channel_id,
        )

    # Flujo rápido: construir mensaje en MarkdownV2
    else:
        if not payload.title or payload.current_price is None:
            raise TelegramNotifyPayloadInvalid()
        ok = bot.send_deal(
            title=payload.title,
            current_price=payload.current_price,
            affiliate_url=payload.affiliate_url or "",
            previous_price=payload.previous_price,
            discount_percentage=payload.discount_percentage,
            short_description=payload.short_description,
            image_url=payload.image_url,
            public_url=payload.public_url,
            chat_id=channel_id,
        )

    if not ok:
        raise TelegramSendFailed()

    await audit_log(
        db,
        user_id=str(current_user.id),
        action="telegram.notify",
        target_type="channel",
        target_id=channel_id,
        payload={"title": payload.title, "has_text": bool(payload.text)},
    )
    return {"ok": True}
