"""Texto de Instagram a partir del post de Telegram que salió de verdad.

En Instagram los enlaces del pie de foto no se pueden pulsar: se quitan las
URLs y la línea de la web, y se remite al enlace de la bio (que apunta a
`/instagram` en la web). Los emojis premium de Telegram no existen aquí: se
cambian por estándar, como en la versión de WhatsApp. Los hashtags de categoría
se conservan (en Instagram sí sirven) y se añaden los fijos de la cuenta.
"""

import re

from app.modules.telegram.application.post_generator import LINK_TEXT

MAX_CAPTION = 2200  # límite de Instagram
MAX_HASHTAGS = 30  # límite de Instagram
BIO_LINE = "🔗 Enlace al chollo en nuestra bio"

_EMOJI_MAP: dict[str, str] = {
    "🍄": "🔥",  # título
    "💶": "🏷️",  # precio (solo si la imagen no es la tarjeta)
    "💰": "💸",  # ahorro
    "✏️": "📝",  # descripción
    "✏": "📝",
    "⚠️": "⏰",  # fin de la oferta
    "⚠": "⏰",
}
_URL = re.compile(r"https?://\S+")
_HASHTAG = re.compile(r"#\w+")
_HASHTAG_LINE = re.compile(r"^(#\w+\s*)+$")


def _convert(line: str) -> str | None:
    stripped = line.strip()
    if stripped.startswith("🛒") or stripped == f"🔗 {LINK_TEXT}":
        return None  # enlaces: van en la bio
    for emoji, replacement in _EMOJI_MAP.items():
        if stripped.startswith(emoji):
            stripped = f"{replacement} {stripped[len(emoji):].strip()}"
            break
    stripped = _URL.sub("", stripped).strip()
    return stripped


def to_instagram_caption(telegram_text: str, fixed_hashtags: str = "") -> str:
    lines: list[str] = []
    tags: list[str] = []
    for raw in telegram_text.splitlines():
        if _HASHTAG_LINE.match(raw.strip()):
            tags += _HASHTAG.findall(raw)
            continue
        line = _convert(raw)
        if line is None:
            continue
        lines.append(line)

    body = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    # Fijos: «chollos ofertas» o «#chollos, #ofertas» (en el .env, sin «#»).
    for word in re.split(r"[\s,#]+", fixed_hashtags or ""):
        tag = f"#{word}"
        if word and _HASHTAG.fullmatch(tag) and tag.lower() not in {t.lower() for t in tags}:
            tags.append(tag)
    hashtags = " ".join(tags[:MAX_HASHTAGS])

    tail = f"\n\n{BIO_LINE}" + (f"\n\n{hashtags}" if hashtags else "")
    room = MAX_CAPTION - len(tail)
    if len(body) > room:
        body = body[: max(0, room - 1)].rstrip() + "…"
    return f"{body}{tail}"
