"""fix auth_rls_initplan on user_roles policy (Supabase Advisor WARN, TD-20)

Revision ID: 20260905120000
Revises: 20260902120000
Create Date: 2026-09-05

La política "Users view own role" reevaluaba auth.uid() fila a fila.
Envolverla en (select ...) hace que el planner la trate como InitPlan
(una sola evaluación por query) — recomendación estándar de Supabase.
Ver docs/project/10-technical-debt.md TD-20.
"""
from alembic import op

revision = "20260905120000"
down_revision = "20260902120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('DROP POLICY IF EXISTS "Users view own role" ON public.user_roles;')
    op.execute(
        'CREATE POLICY "Users view own role" ON public.user_roles '
        "FOR SELECT USING ((select auth.uid()) = user_id);"
    )


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS "Users view own role" ON public.user_roles;')
    op.execute(
        'CREATE POLICY "Users view own role" ON public.user_roles '
        "FOR SELECT USING (auth.uid() = user_id);"
    )
