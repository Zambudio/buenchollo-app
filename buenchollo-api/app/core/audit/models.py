"""Modelo SQLAlchemy del audit log.

Tabla `admin_audit_log`: registra acciones críticas de admin para
trazabilidad y debugging post-mortem. Independiente del módulo que la
dispara — cualquier capa puede llamar a `audit_log(...)`.

Columnas:

- `id`            UUID server-side (gen_random_uuid).
- `user_id`       UUID del admin que ejecutó la acción.
- `action`        Identificador corto de la acción (deal.create, deal.delete,
                  category.create, etc.). Convención: `<dominio>.<verbo>`.
- `target_type`   Tipo de entidad afectada (deal, category, store, user, ...).
- `target_id`     Identificador de la entidad afectada (puede ser None
                  para acciones agregadas como bulk_import).
- `payload`       JSONB con datos del cambio (snapshot del before/after,
                  o el body relevante).
- `request_id`    Correlation id de la petición (ver `core/request_id.py`)
                  para cruzar con los logs estructurados.
- `created_at`    Timestamp con zona horaria.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base

# Importa Profile para que la FK user_id → profiles.user_id se resuelva al
# instanciar el mapper (mismo patrón que en deals/domain/models.py).
import app.modules.users.domain.models  # noqa: F401


class AuditLog(Base):
    __tablename__ = "admin_audit_log"

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("profiles.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
