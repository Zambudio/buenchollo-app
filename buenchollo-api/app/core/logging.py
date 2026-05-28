"""Configuración de logging.

Dos formatos soportados (controlado por `Settings.log_format`):

- **`json`** (recomendado en producción/Docker): una línea JSON por log
  con `ts`, `level`, `logger`, `msg`, `request_id` y cualquier campo
  extra que se pase con `extra=...`. Pensado para que Loki, ELK o un
  agregador parsee directamente.
- **`text`** (recomendado en desarrollo): formato legible
  `ts  LEVEL [logger] [req=...] mensaje`.

El `request_id` se obtiene del `ContextVar` rellenado por
`RequestIdMiddleware`. Si no hay request en curso (p. ej. scheduler de
APScheduler o arranque de la app), aparece como `-`.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.core.request_id import get_request_id


# Atributos estándar de LogRecord que NO queremos duplicar en `extra` del JSON.
_LOGRECORD_RESERVED_ATTRS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "asctime", "taskName",
}


class _RequestIdFilter(logging.Filter):
    """Inyecta `record.request_id` en cada log con el valor del ContextVar."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True


class _JsonFormatter(logging.Formatter):
    """Formatea cada record como JSON de una sola línea."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)

        # Campos extra pasados con `logger.info("...", extra={"foo": 1})`
        for key, value in record.__dict__.items():
            if key in _LOGRECORD_RESERVED_ATTRS or key in payload:
                continue
            if key.startswith("_"):
                continue
            try:
                json.dumps(value)
            except (TypeError, ValueError):
                value = repr(value)
            payload[key] = value

        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str, fmt: str = "json") -> None:
    """Configura el logging raíz. Llamar una sola vez al arrancar la app.

    `fmt`:
        "json" para logs estructurados (producción), "text" para legible
        (desarrollo). Cualquier otro valor cae a "text" por defensa.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    handler = logging.StreamHandler()
    handler.addFilter(_RequestIdFilter())
    if fmt == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)-7s [%(name)s] [req=%(request_id)s] %(message)s",
            )
        )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(log_level)
