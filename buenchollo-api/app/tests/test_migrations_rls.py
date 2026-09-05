"""Regresión (ADR-006): toda tabla de `public` creada en una migración debe
activar RLS en alguna migración.

`scheduled_deals` se saltó esta regla al crearse (`20260720120000_scheduled_deals.py`)
y Supabase lo marcó como `rls_disabled_in_public` crítico — ver
`PROJECT_STATUS.md` § 3.tervicies.

Este test NO consulta la BD: el esquema de test se crea con `create_all` (sin
RLS), así que una comprobación contra `pg_tables.rowsecurity` daría siempre
falso. La fuente de verdad del esquema real de producción son los ficheros de
migración, y eso es lo que se escanea aquí.
"""
import re
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parents[2]
_ALEMBIC = _API_ROOT / "alembic" / "versions"
_SUPABASE = _API_ROOT / "supabase" / "migrations"

# `alembic_version` la gestiona el propio Alembic; el resto de nombres que
# aparezcan como `CREATE TABLE public.X` sí deben activar RLS.
_IGNORED: set[str] = {"alembic_version"}

_ALEMBIC_CREATE = re.compile(r"""op\.create_table\(\s*["']([a-z0-9_]+)["']""")
_SQL_CREATE = re.compile(
    r"""create\s+table\s+(?:if\s+not\s+exists\s+)?public\.([a-z0-9_]+)""", re.I
)
_RLS_ENABLE = re.compile(
    r"""alter\s+table\s+public\.([a-z0-9_]+)\s+enable\s+row\s+level\s+security""", re.I
)


def _scan(pattern: re.Pattern, folder: Path, glob: str) -> set[str]:
    found: set[str] = set()
    for f in folder.glob(glob):
        found |= {m.lower() for m in pattern.findall(f.read_text(encoding="utf-8"))}
    return found


def test_toda_tabla_public_de_una_migracion_activa_rls():
    created = _scan(_ALEMBIC_CREATE, _ALEMBIC, "*.py") | _scan(_SQL_CREATE, _SUPABASE, "*.sql")
    created -= _IGNORED

    rls_enabled = _scan(_RLS_ENABLE, _ALEMBIC, "*.py") | _scan(_RLS_ENABLE, _SUPABASE, "*.sql")

    sin_rls = sorted(created - rls_enabled)
    assert not sin_rls, (
        "Tablas de `public` creadas en una migración sin ENABLE ROW LEVEL SECURITY "
        f"(ADR-006): {sin_rls}. Añade en la misma migración "
        "`op.execute(\"ALTER TABLE public.<t> ENABLE ROW LEVEL SECURITY;\")`."
    )
