"""Qué canales de Telegram cuentan para cada red (configuración compartida).

Vive en `core` porque lo consultan varios módulos: `telegram` (para saber si la
copia «versión WhatsApp» al canal Admin sobra) y `whatsapp` (para encolar). Así
ninguno importa al otro.
"""

from app.core.config import Settings


def channel_kind(channel_id: str | None, settings: Settings) -> str | None:
    """`main`, `admin` o None según el canal de Telegram."""
    target = str(channel_id or "").strip()
    if not target:
        return None
    if target == (settings.telegram_main_channel_id or "").strip():
        return "main"
    if target == (settings.telegram_admin_channel_id or "").strip():
        return "admin"
    return None


def whatsapp_publishes(channel_id: str | None, settings: Settings) -> bool:
    """Si lo publicado en ese canal de Telegram sale solo en el Canal de
    WhatsApp (`WHATSAPP_ENABLED` y el canal está en `WHATSAPP_CHANNELS`)."""
    if not settings.whatsapp_enabled:
        return False
    kind = channel_kind(channel_id, settings)
    kinds = {k.strip().lower() for k in (settings.whatsapp_channels or "").split(",")}
    return kind is not None and kind in kinds
