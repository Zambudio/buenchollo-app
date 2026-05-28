"""Service layer del audit log.

Expone una única función `audit_log(...)` que cualquier router/service puede
invocar tras una operación admin para dejar constancia.

Convención de `action`: `<dominio>.<verbo>` en minúsculas, ejemplos:
    deal.create, deal.update, deal.delete
    category.create, category.delete
    store.create, store.update, store.delete
    user.promote, user.demote
    telegram.notify

El `request_id` se toma automáticamente del contextvar de
`core/request_id.py` para correlacionar con los logs estructurados.

Política de errores: el audit log es **best-effort**. Si la inserción
falla (BD caída, JSON no serializable, etc.) se registra el incidente
en el logger pero NO se propaga la excepción al endpoint que ya completó
su operación. Auditar es secundario; el flujo principal no se rompe.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit.models import AuditLog
from app.core.request_id import get_request_id

logger = logging.getLogger(__name__)


async def audit_log(
    session: AsyncSession,
    *,
    user_id: str | None,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    """Registra una acción admin en `admin_audit_log`.

    Best-effort: cualquier error se loguea pero NO se propaga.

    Args:
        session: sesión SQLAlchemy de la petición en curso. Se hace flush
            pero no commit (el `get_db` global comitea al final).
        user_id: id del admin que ejecutó la acción. `None` si la acción
            la disparó un job de sistema.
        action: identificador `<dominio>.<verbo>`.
        target_type: tipo de entidad afectada (`deal`, `category`...).
        target_id: id de la entidad. `None` si es una acción agregada.
        payload: dict serializable como JSON con detalles relevantes.
    """
    sanitized_payload = _sanitize_payload(payload)
    entry = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        payload=sanitized_payload,
        request_id=get_request_id(),
    )
    # SAVEPOINT: si la inserción falla (tabla inexistente, JSON inválido…),
    # el rollback queda contenido en esta subtransacción y la sesión principal
    # del endpoint sigue siendo usable. Sin esto, un fallo de flush envenena
    # la sesión y revienta cualquier query posterior con PendingRollbackError.
    try:
        async with session.begin_nested():
            session.add(entry)
            await session.flush()
        logger.info(
            "audit_log: %s by user=%s target=%s/%s",
            action, user_id, target_type, target_id,
            extra={"audit_action": action, "audit_user_id": user_id},
        )
    except Exception:
        # Audit NO puede romper el endpoint. Sólo dejamos rastro del fallo.
        logger.exception(
            "audit_log: fallo al persistir acción %s (user=%s, target=%s/%s)",
            action, user_id, target_type, target_id,
        )


def _sanitize_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """Verifica que el payload sea serializable. Si algún valor no lo es,
    se cambia por `repr(value)`. Devuelve None si el payload entero es None.

    Evita meter en BD objetos que luego no se puedan leer (datetimes
    pasados por error, SQLAlchemy Row, etc.).
    """
    if not payload:
        return None
    cleaned: dict[str, Any] = {}
    for key, value in payload.items():
        try:
            json.dumps(value, default=str)
            cleaned[key] = value
        except (TypeError, ValueError):
            cleaned[key] = repr(value)
    return cleaned
