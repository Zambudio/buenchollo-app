"""Texto del Canal de WhatsApp a partir del post de Telegram que salió de verdad.

La «versión WhatsApp» (emojis estándar, `*negritas*`, enlace visible a
`/whatsapp`) la prepara quien emite el evento (Telegram) y llega en
`whatsapp_text`; este módulo no conoce el formato de Telegram. Con tarjeta de
oferta se quitan las líneas de precio y ahorro, que ya van en la imagen.
"""

import re

# Nuestros posts rondan los 400 caracteres; por si acaso, nunca más de esto.
MAX_TEXT = 4000

_PRICE_EMOJIS = ("🏷️", "🏷", "💸", "💶", "💰")


def strip_price_lines(text: str) -> str:
    kept = "".join(
        line for line in text.splitlines(keepends=True) if not line.lstrip("* ").startswith(_PRICE_EMOJIS)
    )
    return re.sub(r"\n{3,}", "\n\n", kept).strip()


def channel_text(telegram_text: str | None, *, edited: str | None = None, with_card: bool) -> str:
    """`edited` es la versión WhatsApp; sin ella (no debería pasar) se usa el
    texto de Telegram tal cual."""
    text = (edited or "").strip() or (telegram_text or "").strip()
    if with_card:
        text = strip_price_lines(text)
    return text.strip()[:MAX_TEXT]
