"""revoke public EXECUTE on trigger-only SECURITY DEFINER functions (TD-20)

Revision ID: 20260905120500
Revises: 20260905120000
Create Date: 2026-09-05

handle_new_user / recalc_comment_votes / recalc_blog_comment_votes son
SECURITY DEFINER usadas solo como triggers (verificado: RETURNS trigger,
0 argumentos, ver docs/superpowers/plans/2026-09-05-supabase-advisor-hardening.md
Task 1.1), pero Supabase concede EXECUTE por defecto a anon/authenticated
sobre toda función de `public`, así que PostgREST las expone en
/rest/v1/rpc/<fn>. Revocar EXECUTE no afecta a la ejecución como trigger
(el trigger manager la invoca directamente, sin pasar por el chequeo de
privilegio de "llamar función" de la sesión).
"""
from alembic import op

revision = "20260905120500"
down_revision = "20260905120000"
branch_labels = None
depends_on = None

_FUNCTIONS = ("handle_new_user", "recalc_comment_votes", "recalc_blog_comment_votes")


def upgrade() -> None:
    for fn in _FUNCTIONS:
        op.execute(f"REVOKE EXECUTE ON FUNCTION public.{fn}() FROM PUBLIC, anon, authenticated;")


def downgrade() -> None:
    for fn in _FUNCTIONS:
        op.execute(f"GRANT EXECUTE ON FUNCTION public.{fn}() TO PUBLIC, anon, authenticated;")
