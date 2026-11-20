"""Versión para WhatsApp del post de Telegram.

WhatsApp no tiene los emojis premium animados ni enlaces con texto: se cambian
los iconos por emojis estándar, se pone la URL de la web visible, las negritas
pasan a `*...*` y se quitan los hashtags de categoría (solo sirven en el canal
de Telegram). El admin copia o comparte el resultado a mano en su Canal.
"""

import re

from app.modules.telegram.application.post_generator import LINK_TEXT

# /whatsapp redirige con utm_source=whatsapp: las visitas se miden aparte.
WHATSAPP_LINK_URL = "https://buenchollotech.com/whatsapp"

# Emoji del post de Telegram → (emoji en WhatsApp, línea en negrita)
_EMOJI_MAP: dict[str, tuple[str, bool]] = {
    "🍄": ("🔥", True),    # Título
    "💶": ("🏷️", True),    # Precio
    "💰": ("💸", True),    # Ahorro
    "🛒": ("👉", False),   # Enlace de compra
    "✏️": ("📝", False),   # Descripción
    "✏": ("📝", False),    # (sin selector de variación, si se editó a mano)
    "⚠️": ("⏰", False),   # Fin de oferta
    "⚠": ("⏰", False),
    "🔗": ("🌐", False),   # Enlace a la web
}

_HASHTAG_LINE = re.compile(r"^(#\w+\s*)+$")


def _convert_line(line: str) -> str:
    stripped = line.strip()
    if stripped == f"🔗 {LINK_TEXT}":
        return f"🌐 {LINK_TEXT}: {WHATSAPP_LINK_URL}"
    for premium, (emoji, bold) in _EMOJI_MAP.items():
        if stripped.startswith(premium):
            content = stripped[len(premium):].strip()
            if bold:
                content = f"*{content.replace('*', '')}*"
            return f"{emoji} {content}"
    return line


def to_whatsapp_text(telegram_text: str) -> str:
    lines = [
        _convert_line(line)
        for line in telegram_text.splitlines()
        if not _HASHTAG_LINE.match(line.strip())
    ]
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()
