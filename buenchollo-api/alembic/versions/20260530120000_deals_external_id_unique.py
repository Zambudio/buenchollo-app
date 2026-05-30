"""unique partial index on deals.external_id

Garantiza que dos chollos no puedan compartir ASIN. El índice es parcial
(WHERE external_id IS NOT NULL) para permitir múltiples deals manuales
sin ASIN — `external_id` sólo se rellena cuando viene de Amazon (preview
de productos) y futuras integraciones que produzcan un identificador
externo único.

Pre-flight: si en producción hubiera duplicados, esta migración fallará.
Ejecutar antes:

    SELECT external_id, COUNT(*), array_agg(id ORDER BY created_at)
    FROM deals
    WHERE external_id IS NOT NULL
    GROUP BY external_id
    HAVING COUNT(*) > 1;

Sanear manualmente los duplicados y reintentar.

Revision ID: 20260530120000
Revises: 20260528120000
Create Date: 2026-05-30
"""
from alembic import op

revision = "20260530120000"
down_revision = "20260528120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE UNIQUE INDEX uq_deals_external_id "
        "ON deals (external_id) "
        "WHERE external_id IS NOT NULL;"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_deals_external_id;")
