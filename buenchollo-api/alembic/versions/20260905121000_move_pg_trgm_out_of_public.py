"""move pg_trgm extension out of public schema (TD-20)

Revision ID: 20260905121000
Revises: 20260905120500
Create Date: 2026-09-05

`extension_in_public` (Supabase Advisor WARN): pg_trgm vivía en `public` en
vez de `extensions`, donde ya están pgcrypto/uuid-ossp/pg_stat_statements
en este mismo proyecto. Verificado antes de escribir esto (ver
docs/superpowers/plans/2026-09-05-supabase-advisor-hardening.md Task 1.3):
el `search_path` por defecto es `"$user", public, extensions`, así que
`gin_trgm_ops` (usado por ix_deals_title_trgm) sigue resolviendo sin
cambios en el código de la app.
"""
from alembic import op

revision = "20260905121000"
down_revision = "20260905120500"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS extensions;")
    op.execute("GRANT USAGE ON SCHEMA extensions TO anon, authenticated, service_role;")
    op.execute("ALTER EXTENSION pg_trgm SET SCHEMA extensions;")


def downgrade() -> None:
    op.execute("ALTER EXTENSION pg_trgm SET SCHEMA public;")
