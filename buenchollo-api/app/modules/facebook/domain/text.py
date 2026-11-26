"""Texto de Facebook a partir del post de Telegram que salió de verdad.

En Facebook los enlaces sí se pueden pulsar: se conserva el de compra (🛒) y la
línea de la web pasa a una URL visible a `/facebook` (que mide la fuente). Los
emojis premium de Telegram se cambian por estándar, como en Instagram y
WhatsApp. Se conservan los hashtags de categoría y se añaden los fijos. Como el
enlace de compra es de afiliado, se cierra con el aviso (`FACEBOOK_DISCLOSURE`).
"""

import re

# El límite real de Facebook es 63.206; nuestros posts rondan los 400.
MAX_MESSAGE = 5000
MAX_HASHTAGS = 10
SITE_URL = "https://buenchollotech.com/facebook"
SITE_LINE = f"🌐 Todos los chollos en nuestra web: {SITE_URL}"

_EMOJI_MAP: dict[str, str] = {
    "🍄": "🔥",  # título
    "💶": "🏷️",  # precio (solo si la imagen no es la tarjeta)
    "💰": "💸",  # ahorro
    "✏️": "📝",  # descripción
    "✏": "📝",
    "⚠️": "⏰",  # fin de la oferta
    "⚠": "⏰",
}
_HASHTAG = re.compile(r"#\w+")
_HASHTAG_LINE = re.compile(r"^(#\w+\s*)+$")


def _convert(line: str) -> str | None:
    stripped = line.strip()
    if stripped.startswith("🔗"):
        return None  # enlace a la web (en Telegram, texto con enlace): va al final con URL visible
    for emoji, replacement in _EMOJI_MAP.items():
        if stripped.startswith(emoji):
            return f"{replacement} {stripped[len(emoji):].strip()}"
    return stripped


def to_facebook_text(telegram_text: str, fixed_hashtags: str = "", disclosure: str = "") -> str:
    lines: list[str] = []
    tags: list[str] = []
    for raw in telegram_text.splitlines():
        if _HASHTAG_LINE.match(raw.strip()):
            tags += _HASHTAG.findall(raw)
            continue
        line = _convert(raw)
        if line is not None:
            lines.append(line)

    body = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    for word in re.split(r"[\s,#]+", fixed_hashtags or ""):
        tag = f"#{word}"
        if word and _HASHTAG.fullmatch(tag) and tag.lower() not in {t.lower() for t in tags}:
            tags.append(tag)

    tail = [SITE_LINE]
    if disclosure.strip():
        tail.append(disclosure.strip())
    if tags:
        tail.append(" ".join(tags[:MAX_HASHTAGS]))
    tail_text = "\n\n" + "\n\n".join(tail)
    room = MAX_MESSAGE - len(tail_text)
    if len(body) > room:
        body = body[: max(0, room - 1)].rstrip() + "…"
    return f"{body}{tail_text}"
