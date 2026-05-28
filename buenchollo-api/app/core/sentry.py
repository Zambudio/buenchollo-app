"""Integración opcional con Sentry (o cualquier endpoint compatible
con su protocolo, p. ej. GlitchTip).

Diseño:

- **Activación por env**: si `SENTRY_DSN` está vacío, no se inicializa nada.
  Local y tests quedan inertes sin tocar nada.
- **request_id como tag**: cada evento se etiqueta con el `request_id`
  del contextvar de `core/request_id.py`. Así, cuando veas un error en
  el dashboard de Sentry, puedes cruzarlo con los logs JSON del NAS
  buscando por ese mismo id.
- **Integraciones**: FastAPI, Starlette y SQLAlchemy las habilita Sentry
  por defecto al detectarlas. La integración de logging la dejamos
  configurada para que `logger.exception(...)` mande evento automático.

Uso:

    # En main.py
    from app.core.sentry import init_sentry
    init_sentry(settings)
"""
from __future__ import annotations

import logging
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

from app.core.config import Settings
from app.core.request_id import get_request_id

logger = logging.getLogger(__name__)


def _before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """Hook que se ejecuta por cada evento antes de enviarlo a Sentry.

    - Añade el `request_id` como tag de primer nivel (búsqueda rápida en
      el dashboard).
    - Permite filtrar en el futuro: devolviendo `None` se descarta el evento.
    """
    rid = get_request_id()
    if rid:
        event.setdefault("tags", {})["request_id"] = rid
    return event


def init_sentry(settings: Settings) -> bool:
    """Inicializa Sentry si está configurado. Devuelve True si activó algo.

    Llamar una sola vez al arrancar la app. Si falla (DSN inválido, red
    caída), registra el error en logs y NO propaga: arrancar la app sin
    Sentry es preferible a no arrancar.
    """
    if not settings.sentry_dsn:
        logger.info("Sentry desactivado (SENTRY_DSN vacío).")
        return False

    try:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.sentry_environment or settings.app_env,
            release=settings.sentry_release or None,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            # LoggingIntegration: cualquier logger.error/exception se
            # convierte en evento Sentry automáticamente, sin código extra.
            integrations=[
                LoggingIntegration(
                    level=logging.INFO,      # nivel mínimo para breadcrumbs
                    event_level=logging.ERROR,  # nivel para crear evento
                ),
            ],
            before_send=_before_send,
            send_default_pii=False,  # no enviamos cookies/headers/usuarios por defecto
        )
        logger.info(
            "Sentry inicializado (env=%s, traces=%.2f).",
            settings.sentry_environment or settings.app_env,
            settings.sentry_traces_sample_rate,
        )
        return True
    except Exception:
        # No queremos que un fallo de Sentry impida arrancar la app.
        logger.exception("Sentry no se pudo inicializar; se continúa sin tracking.")
        return False
