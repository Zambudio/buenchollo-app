"""add pg_trgm extension and GIN trigram index on deals.title

Revision ID: 20260829140000
Revises: 20260829120000
Create Date: 2026-08-29
"""
from alembic import op

revision = "20260829140000"
down_revision = "20260829120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Activar extension pg_trgm si no existe
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_deals_title_trgm "
            "ON deals USING gin (title gin_trgm_ops);"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_deals_title_trgm;")
