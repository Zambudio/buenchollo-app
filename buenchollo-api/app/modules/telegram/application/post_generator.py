"""Genera el texto formateado para publicaciones de Telegram y sugiere categorías vía IA."""

import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

# IDs de Custom Emojis Premium de Telegram (iguales a la app Python de referencia)
CUSTOM_EMOJI_MAP: dict[str, str] = {
    "🍄": "5242687246162731515",   # Título
    "💶": "5201873447554145566",   # Precio
    "💰": "5296355151743838259",   # Ahorro
    "🛒": "5346056560537779652",   # URL
    "✏️": "5395444784611480792",   # Descripción
    "⚠️": "5420323339723881652",   # Fin de oferta
}

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


class TelegramPostGenerator:
    """Formatea el texto de un chollo para Telegram y sugiere categorías con GPT."""

    def __init__(self, openai_api_key: str = "") -> None:
        self._openai_key = openai_api_key

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
        price_str = f"{current_price:.2f} €"

        msg = f"🍄 {title}\n\n"

        if previous_price:
            msg += f"💶 Precio: {price_str} (antes {previous_price:.2f} €)\n"
        else:
            msg += f"💶 Precio: {price_str}\n"

        if previous_price and previous_price > current_price:
            savings = previous_price - current_price
            pct_str = f" | -{discount_pct} %" if discount_pct else ""
            msg += f"💰 Ahorro: {savings:.2f} €{pct_str}\n\n"
        else:
            msg += "\n"

        msg += f"🛒 {affiliate_url}\n\n"

        if description:
            msg += f"✏️{_strip_markdown(description.strip())}\n\n"

        if expires_at:
            try:
                iso = expires_at.replace("Z", "+00:00")
                dt = datetime.fromisoformat(iso)
                msg += f"⚠️ Finaliza el {dt.day} de {_MONTHS_ES[dt.month]}\n"
            except Exception:
                pass

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

        # Negrita sobre todo el mensaje
        total = len(text.encode("utf-16-le")) // 2
        entities.append({"type": "bold", "offset": 0, "length": total})
        return entities

    # ── Sugerencia de categorías con GPT ─────────────────────────────────────

    async def suggest_categories(
        self,
        title: str,
        description: str,
        available: list[str],
    ) -> list[str]:
        """Llama a GPT-4o-mini para elegir 1-2 hashtags del catálogo disponible."""
        if not available or not self._openai_key:
            return []

        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self._openai_key)

            cats_str = " ".join(available)
            prompt = (
                "Elige 1 o 2 hashtags de esta lista que mejor describan el producto.\n"
                "Solo puedes usar hashtags de la lista. Responde solo con los hashtags.\n\n"
                f"Lista: {cats_str}\n"
                f"Producto: {title}\n{description}"
            )

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Solo puedes usar las categorías proporcionadas."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            raw = response.choices[0].message.content.strip()
            tokens = raw.replace(",", " ").split()
            allowed = set(available)
            return [t for t in tokens if t in allowed][:2]

        except Exception as exc:
            logger.warning("Sugerencia de categorías GPT falló: %s", exc)
            return []
