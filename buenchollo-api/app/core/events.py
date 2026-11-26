"""Bus de eventos en proceso: desacopla los módulos que publican algo de los que
reaccionan (otras redes, avisos al administrador…).

Quien emite no conoce a quien escucha: `telegram` anuncia «chollo publicado» y
`instagram` (o la red que venga después) se suscribe en el arranque
(`app.core.bootstrap.register_subscribers`). Un suscriptor que falla nunca
afecta al emisor ni a los demás: se registra y se sigue.

Es deliberadamente mínimo (en memoria, dentro del mismo proceso y de la misma
transacción de BD del emisor); si algún día hace falta entre procesos, se
sustituye por una cola sin tocar a los emisores.
"""

from __future__ import annotations

import inspect
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

Handler = Callable[[Any], Awaitable[None] | None]

_handlers: dict[type, list[Handler]] = defaultdict(list)


@dataclass(frozen=True)
class DealPostPublished:
    """Un chollo acaba de salir en un canal de Telegram.

    `session` es la sesión de BD del emisor: lo que el suscriptor guarde entra en
    la misma transacción (en un savepoint propio). `download` descarga una
    imagen con las defensas del emisor (SSRF, tamaño), por si `card` es None."""

    session: Any
    channel_id: str
    text: str
    deal_id: str | None = None
    card: bytes | None = None
    image_url: str | None = None
    download: Callable[[str], bytes | None] | None = None
    # Versión WhatsApp del post (la editada en el panel o la generada por
    # Telegram): así `whatsapp` no depende del formato de Telegram.
    whatsapp_text: str | None = None


@dataclass(frozen=True)
class WhatsAppPostRequested:
    """Publicación para el Canal de WhatsApp que no sale de `DealPostPublished`
    (hoy, el resumen semanal). Quien escucha abre su propia sesión de BD."""

    telegram_text: str
    whatsapp_text: str | None = None
    image: bytes | None = None
    # Quitar las líneas de precio y ahorro (solo si la imagen es la tarjeta de oferta).
    strip_prices: bool = False
    deal_id: str | None = None


@dataclass(frozen=True)
class AdminAlert:
    """Aviso para el administrador (hoy, al canal Admin de Telegram)."""

    text: str


def subscribe(event_type: type, handler: Handler) -> None:
    if handler not in _handlers[event_type]:
        _handlers[event_type].append(handler)


def clear() -> None:
    """Solo para tests."""
    _handlers.clear()


def subscribers(event_type: type) -> list[Handler]:
    return list(_handlers.get(event_type, ()))


async def publish(event: Any) -> None:
    """Entrega el evento a cada suscriptor, en orden. Nunca lanza."""
    for handler in subscribers(type(event)):
        try:
            result = handler(event)
            if inspect.isawaitable(result):
                await result
        except Exception:
            logger.exception("Suscriptor %s falló con %s", getattr(handler, "__qualname__", handler), type(event).__name__)
