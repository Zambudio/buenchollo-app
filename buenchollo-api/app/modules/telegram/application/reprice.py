"""Corrige el precio de una publicación de Telegram ya enviada para volver a
publicarla: cambia solo las líneas de precio, ahorro y fecha de fin (con el
formato de `TelegramPostGenerator`) y respeta el resto del texto, aunque se
editara a mano en el panel."""

from datetime import datetime
from decimal import Decimal

from app.modules.telegram.application.post_generator import _MONTHS_ES, _format_price_es

_PRICE = "💶"
_SAVINGS = "💰"
_ENDS = "⚠️ Finaliza el"


def reprice_publication_text(
    text: str,
    *,
    price: Decimal,
    previous_price: Decimal | None,
    discount_pct: int | None,
    expires_at: datetime | None,
    now: datetime,
) -> str | None:
    """Devuelve el texto corregido, o None si no tiene la línea de precio del
    formato estándar (el llamante genera entonces una publicación nueva)."""
    lines = text.split("\n")
    index = next((i for i, line in enumerate(lines) if line.startswith(_PRICE)), None)
    if index is None:
        return None

    price_text = f"{_format_price_es(float(price))} €"
    if previous_price:
        lines[index] = f"{_PRICE} Precio: {price_text} (antes {_format_price_es(float(previous_price))} €)"
    else:
        lines[index] = f"{_PRICE} Precio: {price_text}"

    if index + 1 < len(lines) and lines[index + 1].startswith(_SAVINGS):
        del lines[index + 1]
    if previous_price and previous_price > price:
        pct = f" | -{discount_pct} %" if discount_pct else ""
        lines.insert(index + 1, f"{_SAVINGS} Ahorro: {_format_price_es(float(previous_price - price))} €{pct}")

    ends = next((i for i, line in enumerate(lines) if line.startswith(_ENDS)), None)
    if ends is not None:
        if expires_at is not None and expires_at > now:
            lines[ends] = f"{_ENDS} {expires_at.day} de {_MONTHS_ES[expires_at.month]}"
        else:
            del lines[ends]
            if ends < len(lines) and lines[ends] == "":
                del lines[ends]
    return "\n".join(lines)
