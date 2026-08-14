"""Genera el texto formateado para publicaciones de Telegram y sugiere categorías vía IA."""

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
    "🛒": "5346056560537779652",   # URL
    "✏️": "5395444784611480792",   # Descripción
    "⚠️": "5420323339723881652",   # Fin de oferta
    "🔗": "5282843764451195532",   # Enlace web
}

LINK_TEXT = "Todos los chollos en nuestra web"
LINK_URL = "https://buenchollotech.com"

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

        msg += f"🔗 {LINK_TEXT}\n\n"

        return msg

    # ── Entidades Telegram Premium ────────────────────────────────────────────

    def build_entities(self, text: str) -> list[dict]:
        """
        Convierte los emojis estándar en Custom Emojis Premium de Telegram
        y añade bold al mensaje completo.
        Cálculo de offsets en UTF-16 LE (requerido por la API de Telegram).
        """
        entities: list[dict] = []

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

