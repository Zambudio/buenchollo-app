"""Registro central de modelos SQLAlchemy para Alembic.

Cada modelo debe importarse aquí para quedar registrado en `Base.metadata`,
que es lo que Alembic compara contra la BD real al generar migraciones con
`--autogenerate`.

Tablas auxiliares **no modeladas en Python** (gestionadas con SQL puro vía
`text(...)`):

- `user_roles` (deal_repository / security usan SQL parametrizado).
- `import_logs` (logs históricos, sin lógica en Python).

Estas tablas existen en la BD pero no figuran en `Base.metadata`. El filtro
`include_object` de `alembic/env.py` impide que Alembic intente dropearlas
durante un `--autogenerate`. Si en el futuro las gestionamos desde Python,
basta con declarar el modelo y eliminar la entrada del filtro.
"""
from app.core.database import Base

# Modelos por módulo (importar es suficiente para registrarlos en Base.metadata)
from app.modules.categories.domain.models import Category  # noqa: F401
from app.modules.stores.domain.models import Store  # noqa: F401
from app.modules.users.domain.models import Profile  # noqa: F401
from app.modules.deals.domain.models import Deal, DealVote, Favorite  # noqa: F401
from app.modules.alerts.domain.models import Alert  # noqa: F401
from app.modules.notifications.domain.models import Notification  # noqa: F401
from app.modules.comments.domain.models import DealComment, CommentVote  # noqa: F401

# Audit log (vive en core/ porque cualquier módulo puede escribir en él)
from app.core.audit.models import AuditLog  # noqa: F401

__all__ = ["Base"]
