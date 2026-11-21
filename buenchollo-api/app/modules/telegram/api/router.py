from datetime import datetime, timezone
from uuid import UUID
import asyncio
from fastapi import APIRouter, Depends, Request, Response
from starlette.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_log
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import require_admin
from app.modules.deals.infrastructure.repository import DealRepository
from app.modules.deals.application.deal_service import _GUARD_FIELDS
from app.modules.affiliates.application.programs import PublicationBlocked, PublicationGuard
from app.modules.affiliates.domain.offers import NETWORK_TRACKING_HOSTS
from app.modules.affiliates.infrastructure.repository import AffiliateRepository
from app.modules.telegram.application.post_generator import TelegramPostGenerator
from app.modules.telegram.application.whatsapp_copy import send_whatsapp_copy
from app.modules.telegram.application.whatsapp_formatter import to_whatsapp_text
from app.modules.telegram.application.weekly_digest import build_weekly_digest_service
from app.modules.telegram.application.publications import channel_kind, record_safely, with_current_price
from app.modules.telegram.infrastructure.publication_repository import TelegramPublicationRepository
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
    TelegramPublicationResponse,
    WhatsAppTextRequest,
    WhatsAppTextResponse,
    WeeklyDigestResponse,
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
    generator = TelegramPostGenerator(settings=settings)

    ai_copy = (
        await generator.generate_copy(
            title=payload.title,
            details=payload.copy_context or payload.description or "",
            provider=payload.provider,
        )
        if payload.ai_copy
        else None
    )

    text = generator.generate_text(
        title=payload.title,
        current_price=payload.current_price,
        previous_price=payload.previous_price,
        discount_pct=payload.discount_percentage,
        description=ai_copy or payload.description,
        affiliate_url=payload.affiliate_url,
        expires_at=payload.expires_at,
        shipping_info=payload.shipping_info,
        notice=payload.notice,
    )

    categories = repo.load()
    suggested: list[str] = []
    try:
        suggested = await asyncio.wait_for(
            generator.suggest_categories(
                title=payload.title,
                description=payload.description or "",
                available=categories,
            ),
            timeout=10.0,
        )
    except Exception:
        from app.modules.ai.infrastructure.telegram_ai_service import TelegramAIService
        suggested = TelegramAIService.extract_heuristic_tags(
            title=payload.title,
            description=payload.description or "",
            available=categories,
        )

    return TelegramGenerateResponse(
        text=text,
        suggested_categories=suggested,
        ai_copy=ai_copy,
        whatsapp_text=to_whatsapp_text(text),
    )


@router.post("/whatsapp-text", response_model=WhatsAppTextResponse)
async def whatsapp_text(
    payload: WhatsAppTextRequest,
    _auth=Depends(require_admin),
) -> WhatsAppTextResponse:
    """Convierte el post de Telegram (ya editado en el panel) a su versión de WhatsApp."""
    return WhatsAppTextResponse(text=to_whatsapp_text(payload.text))


# ── Publicación ────────────────────────────────────────────────────────────────

async def _ensure_network_deal_publishable(db: AsyncSession, payload: TelegramNotifyRequest) -> None:
    """Un post con enlace de Awin/Tradedoubler solo sale si su chollo guardado
    cumple las reglas de publicación (precio anterior con evidencia, envío,
    imagen autorizada, programa aprobado, dato no caducado...)."""
    text = f"{payload.text or ''} {payload.affiliate_url or ''}"
    if not any(host in text for host in NETWORK_TRACKING_HOSTS):
        return
    deal = await DealRepository(db).get_by_id(str(payload.deal_id)) if payload.deal_id else None
    if deal is None:
        raise PublicationBlocked(["affiliate_url"]) from None
    data = {column: getattr(deal, column) for column in _GUARD_FIELDS}
    data["status"] = "active"
    await PublicationGuard(AffiliateRepository(db)).ensure_publishable(data)


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
      y envía además la versión WhatsApp al canal Admin.
    - Si no → construye el mensaje en MarkdownV2 (flujo rápido del checkbox)
    """
    bot = _get_bot(settings)
    await _ensure_network_deal_publishable(db, payload)

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
        ok = await run_in_threadpool(
            bot.send_preformatted,
            text=payload.text,
            entities=entities,
            image_url=payload.image_url,
            chat_id=channel_id,
        )

    # Flujo rápido: construir mensaje en MarkdownV2
    else:
        if not payload.title or payload.current_price is None:
            raise TelegramNotifyPayloadInvalid()
        ok = await run_in_threadpool(
            bot.send_deal,
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

    if payload.text:
        await record_safely(
            db,
            TelegramPublicationRepository(db),
            DealRepository(db),
            text=payload.text,
            channel_id=channel_id,
            kind=channel_kind(channel_id, settings),
            source="panel",
            image_url=payload.image_url,
            deal_id=str(payload.deal_id) if payload.deal_id else None,
            affiliate_url=payload.affiliate_url,
            message_id=bot.last_message_id,
            sent_by=str(current_user.id),
        )

    whatsapp_sent = False
    if payload.text:
        whatsapp_sent = await run_in_threadpool(
            send_whatsapp_copy,
            bot,
            chat_id=settings.telegram_admin_channel_id,
            telegram_text=payload.text,
            image_url=payload.image_url,
            whatsapp_text=payload.whatsapp_text,
        )

    await audit_log(
        db,
        user_id=str(current_user.id),
        action="telegram.notify",
        target_type="channel",
        target_id=channel_id,
        payload={"title": payload.title, "has_text": bool(payload.text), "whatsapp_sent": whatsapp_sent},
    )
    return {"ok": True, "whatsapp_sent": whatsapp_sent}


@router.get("/publications", response_model=list[TelegramPublicationResponse])
async def list_publications(
    deal_id: UUID,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_admin),
) -> list[TelegramPublicationResponse]:
    """Publicaciones enviadas de un chollo, la más reciente primero, con su
    texto ya corregido al precio actual."""
    publications = await TelegramPublicationRepository(db).list_for_deal(str(deal_id))
    deal = await DealRepository(db).get_by_id(str(deal_id))
    repriced = with_current_price(publications, deal, datetime.now(timezone.utc))
    return [
        TelegramPublicationResponse.model_validate(p).model_copy(update={"repriced_text": text})
        for p, text in zip(publications, repriced)
    ]


# ── Resumen semanal «Los chollos de la semana» ────────────────────────────────

@router.get("/weekly-digest", response_model=WeeklyDigestResponse)
async def preview_weekly_digest(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _auth=Depends(require_admin),
):
    """Vista previa del resumen semanal tal y como saldría ahora (no envía nada)."""
    digest = await build_weekly_digest_service(db, settings).preview()
    return WeeklyDigestResponse(
        telegram_text=digest.telegram_text,
        full_text=digest.full_text,
        whatsapp_text=digest.whatsapp_text,
        count=digest.count,
        sent=False
    )


@router.get("/weekly-digest/image", response_class=Response)
@limiter.limit("20/hour")
async def preview_weekly_digest_image(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _auth=Depends(require_admin),
):
    """Collage del resumen semanal tal y como saldría ahora (JPEG; no envía nada)."""
    service = build_weekly_digest_service(db, settings)
    digest = await service.preview()
    image = await run_in_threadpool(service.collage, digest)
    if image is None:
        return Response(status_code=204)
    return Response(content=image, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.post("/weekly-digest/send", response_model=WeeklyDigestResponse)
@limiter.limit("5/hour")
async def send_weekly_digest(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_user=Depends(require_admin),
):
    """Envía ahora el resumen semanal al canal Admin (versiones Telegram y WhatsApp)."""
    service = build_weekly_digest_service(db, settings)
    digest = await service.preview()
    sent = await run_in_threadpool(service.send, digest)
    await audit_log(
        db,
        user_id=str(current_user.id),
        action="telegram.weekly_digest.send",
        target_type="channel",
        target_id="admin",
        payload={"count": digest.count, "sent": sent},
    )
    return WeeklyDigestResponse(
        telegram_text=digest.telegram_text,
        full_text=digest.full_text,
        whatsapp_text=digest.whatsapp_text,
        count=digest.count,
        sent=sent
    )
