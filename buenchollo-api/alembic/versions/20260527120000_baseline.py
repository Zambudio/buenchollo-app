"""baseline — estado actual del esquema en producción (2026-05-27)

Migración VACÍA a propósito. Su única función es servir de punto de partida
para Alembic. Las tablas, triggers, funciones y policies actuales fueron
creadas por las migraciones SQL en `buenchollo-api/supabase/migrations/`
(de 2026-04-20 a 2026-05-27) y ya están aplicadas en producción.

Para registrarla como aplicada sin ejecutar SQL: `alembic stamp head`.

A partir de aquí, todas las nuevas migraciones se generan con Alembic:
    `alembic revision --autogenerate -m "descripción"`

Revision ID: 20260527120000_baseline
Revises:
Create Date: 2026-05-27
"""
from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


revision = "20260527120000_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op. El esquema actual ya está aplicado por las migraciones SQL."""


def downgrade() -> None:
    """No-op. La baseline no se revierte; corresponde al estado inicial."""
