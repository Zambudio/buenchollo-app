"""Texto del Canal de WhatsApp a partir del post de Telegram que salió de verdad.

Es la misma «versión WhatsApp» que llega al canal Admin de Telegram
(`to_whatsapp_text`: emojis estándar, `*negritas*`, enlace visible a
`/whatsapp`). Con tarjeta de oferta se quitan las líneas de precio y ahorro,
que ya van en la imagen. El texto editado a mano en el panel manda.
"""

import re

from app.modules.telegram.application.whatsapp_formatter import to_whatsapp_text

# Nuestros posts rondan los 400 caracteres; por si acaso, nunca más de esto.
MAX_TEXT = 4000

_PRICE_EMOJIS = ("🏷️", "🏷", "💸", "💶", "💰")


def strip_price_lines(text: str) -> str:
    kept = "".join(
        line for line in text.splitlines(keepends=True) if not line.lstrip("* ").startswith(_PRICE_EMOJIS)
    )
    return re.sub(r"\n{3,}", "\n\n", kept).strip()


def channel_text(telegram_text: str | None, *, edited: str | None = None, with_card: bool) -> str:
    text = (edited or "").strip() or to_whatsapp_text(telegram_text or "")
    if with_card:
        text = strip_price_lines(text)
    return text.strip()[:MAX_TEXT]
