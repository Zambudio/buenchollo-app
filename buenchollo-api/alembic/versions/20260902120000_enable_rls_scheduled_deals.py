"""enable RLS on scheduled_deals (rls_disabled_in_public — ADR-006)

Revision ID: 20260902120000
Revises: 20260829140000
Create Date: 2026-09-02

`scheduled_deals` se creó en 20260720120000 SIN activar RLS, saltándose la
regla de ADR-006 (toda tabla nueva de `public` debe activar RLS en la misma
migración). Supabase lo reportó como `rls_disabled_in_public` crítico
(email del 2026-08-31): con el `anon key` público del bundle, cualquiera
podía SELECT/INSERT/DELETE en la cola de publicaciones — incluido inyectar
una fila `programado` con `telegram_text`/`image_url`/`affiliate_url`
arbitrarios que el worker publicaría en el canal de Telegram.

Con RLS activa y 0 políticas, `anon`/`authenticated` quedan denegados. El
backend usa la conexión de servicio (SQLAlchemy directo), que bypassa RLS,
así que el worker de publicaciones sigue operando igual — como con las
otras 21 tablas de `public`.
"""
from alembic import op

revision = "20260902120000"
down_revision = "20260829140000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.scheduled_deals ENABLE ROW LEVEL SECURITY;")


def downgrade() -> None:
    op.execute("ALTER TABLE public.scheduled_deals DISABLE ROW LEVEL SECURITY;")
