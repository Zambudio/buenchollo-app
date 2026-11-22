"""Genera el texto formateado para publicaciones de Telegram y sugiere categorías vía IA."""

import asyncio
import logging
import re
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# IDs de Custom Emojis Premium de Telegram (iguales a la app Python de referencia)
CUSTOM_EMOJI_MAP: dict[str, str] = {
    "🍄": "5242687246162731515",   # Título
    "💶": "5201873447554145566",   # Precio
    "💰": "5296355151743838259",   # Ahorro
    "✏️": "5395444784611480792",   # Descripción
    "⚠️": "5420323339723881652",   # Fin de oferta
    "🔗": "5282843764451195532",   # Enlace web
}

# Icono del enlace de compra (🛒): depende de la tienda. Para añadir una tienda,
# saca el `custom_emoji_id` enviando el emoji premium a @JsonDumpBot (campo
# `entities[].custom_emoji_id`) y añádelo a STORE_LINK_ICONS con una clave que
# aparezca en el nombre de la tienda o en el dominio de su web.
LINK_EMOJI = "🛒"
AMAZON_LINK_ICON = "5346056560537779652"
GENERIC_LINK_ICON = "5271604874419647061"   # tiendas sin icono propio (Coolmod...)
STORE_LINK_ICONS: dict[str, str] = {
    "amazon": AMAZON_LINK_ICON,
    "xiaomi": "5262875916031244720",
    "aliexpress": "5373265917092316632",
    "steam": "5373144051690258848",       # dominio store.steampowered.com
}

# Iconos guardados para más adelante (todavía no se usan en los posts):
# - Samsung: el logo ocupa DOS emojis (izquierda, derecha). El 🛒 es un solo
#   carácter, así que necesita que el post escriba dos emojis base seguidos.
# - WhatsApp: para enlazar el Canal de WhatsApp desde las publicaciones.
SAMSUNG_LINK_ICON_PARTS: tuple[str, str] = ("5307876255486453093", "5309981060044433947")
WHATSAPP_ICON = "5334998226636390258"
_AMAZON_HOST_RE = re.compile(r"(^|\.)(amazon\.[a-z.]+|amzn\.[a-z]+|link\.amazon)$")
_URL_RE = re.compile(r"https?://([^/\s?#]+)", re.I)


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def link_icon_for(url: str | None, store_name: str | None = None) -> str:
    """`custom_emoji_id` del 🛒: la tienda del chollo manda (el enlace de Awin,
    `tidd.ly`, no la dice); sin tienda, se deduce del dominio del enlace."""
    if store_name:
        name = _normalize(store_name)
        for key, icon in STORE_LINK_ICONS.items():
            if key in name:
                return icon
        return GENERIC_LINK_ICON
    match = _URL_RE.search(url or "")
    host = match.group(1).lower() if match else ""
    if _AMAZON_HOST_RE.search(host):
        return AMAZON_LINK_ICON
    for key, icon in STORE_LINK_ICONS.items():
        if key != "amazon" and key in _normalize(host):
            return icon
    return GENERIC_LINK_ICON

# Los modelos gratuitos de OmniRoute pueden tardar; pasado este tiempo se usa la descripción.
COPY_TIMEOUT_SECONDS = 60.0

LINK_TEXT = "Todos los chollos en nuestra web"
LINK_URL = "https://buenchollotech.com/telegram"

_MONTHS_ES = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _strip_markdown(text: str) -> str:
    """
    Elimina marcadores de markdown que GPT incluye en las descripciones
    y que Telegram no renderiza en modo entidades (aparecen como texto literal).
    """
    # **negrita** y *cursiva* → texto plano
    text = re.sub(r"\*{2}([^*]*)\*{2}", r"\1", text)
    text = re.sub(r"\*([^*]*)\*", r"\1", text)
    # __subrayado__ y _cursiva_ → texto plano
    text = re.sub(r"_{2}([^_]*)_{2}", r"\1", text)
    text = re.sub(r"_([^_]*)_", r"\1", text)
    return text


def _format_price_es(value: float) -> str:
    """Formatea un importe en formato español: punto de millar, coma decimal."""
    integer_part, _, decimal_part = f"{value:,.2f}".partition(".")
    return f"{integer_part.replace(',', '.')},{decimal_part}"


from app.modules.ai.domain.ports import TelegramAIServiceProtocol
from app.modules.ai.infrastructure.llm_client import OpenAICompatibleLLMClient
from app.modules.ai.infrastructure.telegram_ai_service import TelegramAIService


class TelegramPostGenerator:
    """Formatea el texto de un chollo para Telegram y sugiere categorías con el motor de IA."""

    def __init__(
        self,
        openai_api_key: str = "",
        ai_service: TelegramAIServiceProtocol | None = None,
        settings: Any | None = None,
    ) -> None:
        self._openai_key = openai_api_key
        if ai_service is not None:
            self._ai_service = ai_service
        elif settings is not None:
            llm_client = OpenAICompatibleLLMClient(settings)
            self._ai_service = TelegramAIService(llm_client)
        elif openai_api_key:
            from app.core.config import Settings
            cfg = Settings(openai_api_key=openai_api_key)
            llm_client = OpenAICompatibleLLMClient(cfg)
            self._ai_service = TelegramAIService(llm_client)
        else:
            from app.core.config import get_settings
            llm_client = OpenAICompatibleLLMClient(get_settings())
            self._ai_service = TelegramAIService(llm_client)

    # ── Generación de texto ────────────────────────────────────────────────────

    def generate_text(
        self,
        title: str,
        current_price: float,
        previous_price: float | None = None,
        discount_pct: int | None = None,
        description: str | None = None,
        affiliate_url: str = "",
        expires_at: str | None = None,
        shipping_info: str | None = None,
        notice: str | None = None,
    ) -> str:
        """Construye el texto del post con emojis en el formato estándar de BuenChollo."""
        price_str = f"{_format_price_es(current_price)} €"

        msg = f"🍄 {title}\n\n"

        if previous_price:
            msg += f"💶 Precio: {price_str} (antes {_format_price_es(previous_price)} €)\n"
        else:
            msg += f"💶 Precio: {price_str}\n"

        if previous_price and previous_price > current_price:
            savings = previous_price - current_price
            pct_str = f" | -{discount_pct} %" if discount_pct else ""
            msg += f"💰 Ahorro: {_format_price_es(savings)} €{pct_str}\n\n"
        else:
            msg += "\n"

        if shipping_info and shipping_info.strip():
            msg += f"🚚 {shipping_info.strip()}\n\n"

        msg += f"🛒 {affiliate_url}\n\n"

        if description:
            msg += f"✏️{_strip_markdown(description.strip())}\n\n"

        if expires_at:
            try:
                iso = expires_at.replace("Z", "+00:00")
                dt = datetime.fromisoformat(iso)
                msg += f"⚠️ Finaliza el {dt.day} de {_MONTHS_ES[dt.month]}\n\n"
            except Exception:
                pass

        if notice and notice.strip():
            msg += f"ℹ️ {notice.strip()}\n\n"

        msg += f"🔗 {LINK_TEXT}\n\n"

        return msg

    # ── Entidades Telegram Premium ────────────────────────────────────────────

    def build_entities(self, text: str, store_name: str | None = None) -> list[dict]:
        """
        Convierte los emojis estándar en Custom Emojis Premium de Telegram
        y añade bold al mensaje completo. El 🛒 de cada línea toma el icono de
        la tienda (`store_name`) o, si no se conoce, el del dominio de su enlace.
        Cálculo de offsets en UTF-16 LE (requerido por la API de Telegram).
        """
        entities: list[dict] = []

        start = 0
        while (idx := text.find(LINK_EMOJI, start)) != -1:
            line_end = text.find("\n", idx)
            line = text[idx : line_end if line_end != -1 else len(text)]
            entities.append({
                "type": "custom_emoji",
                "offset": len(text[:idx].encode("utf-16-le")) // 2,
                "length": len(LINK_EMOJI.encode("utf-16-le")) // 2,
                "custom_emoji_id": link_icon_for(line, store_name),
            })
            start = idx + len(LINK_EMOJI)

        for emoji_char, custom_id in CUSTOM_EMOJI_MAP.items():
            start = 0
            while True:
                idx = text.find(emoji_char, start)
                if idx == -1:
                    break
                offset = len(text[:idx].encode("utf-16-le")) // 2
                length = len(emoji_char.encode("utf-16-le")) // 2
                entities.append({
                    "type": "custom_emoji",
                    "offset": offset,
                    "length": length,
                    "custom_emoji_id": custom_id,
                })
                start = idx + len(emoji_char)

        link_idx = text.find(LINK_TEXT)
        if link_idx != -1:
            offset = len(text[:link_idx].encode("utf-16-le")) // 2
            length = len(LINK_TEXT.encode("utf-16-le")) // 2
            entities.append({
                "type": "text_link",
                "offset": offset,
                "length": length,
                "url": LINK_URL,
            })

        # Negrita sobre todo el mensaje
        total = len(text.encode("utf-16-le")) // 2
        entities.append({"type": "bold", "offset": 0, "length": total})
        return entities

    # ── Copy con IA ───────────────────────────────────────────────────────────

    async def generate_copy(
        self,
        title: str,
        details: str,
        provider: str | None = None,
        timeout: float = COPY_TIMEOUT_SECONDS,
    ) -> str | None:
        """Línea de venta (✏️) del post escrita por la IA. None si no hay motor,
        falla o tarda más de `timeout`: el post se arma entonces con la descripción."""
        if self._ai_service is None:
            return None
        try:
            return await asyncio.wait_for(
                self._ai_service.generate_copy(title=title, details=details, provider=provider),
                timeout=timeout,
            )
        except TimeoutError:
            logger.warning("La IA no generó el copy de Telegram en %.0f s (motor %s)", timeout, provider)
            return None

    # ── Sugerencia de categorías con IA ──────────────────────────────────────

    async def suggest_categories(
        self,
        title: str,
        description: str,
        available: list[str],
    ) -> list[str]:
        """Llama al servicio de IA para elegir 1-2 hashtags del catálogo disponible."""
        if not available or self._ai_service is None:
            return []
        return await self._ai_service.suggest_categories(
            title=title,
            description=description,
            available=available,
        )
