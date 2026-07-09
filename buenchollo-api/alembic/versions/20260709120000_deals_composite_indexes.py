"""composite indexes on deals for latest/popular queries

Añade índices compuestos (status, published_at) y (status, temperature)
para acelerar get_latest_active / get_popular_active (repository.py), que
filtran por status='active' y ordenan por esas columnas.

Usa CREATE INDEX CONCURRENTLY para no bloquear escrituras en `deals`
mientras se construye el índice. CONCURRENTLY no puede ejecutarse dentro
de una transacción, así que se usa autocommit_block() de Alembic, que
hace COMMIT antes del bloque y abre una nueva transacción después.

No se añade índice GIN/pg_trgm para el `ilike` de búsqueda por título
(search_active) — la extensión pg_trgm no está habilitada en este
proyecto; se deja como mejora futura si esa query se convierte en un
cuello de botella medido.

Revision ID: 20260709120000
Revises: 20260707170000
Create Date: 2026-07-09
"""
from alembic import op

revision = "20260709120000"
down_revision = "20260707170000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_deals_status_published_at "
            "ON deals (status, published_at DESC);"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_deals_status_temperature "
            "ON deals (status, temperature DESC);"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_deals_status_published_at;")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_deals_status_temperature;")
