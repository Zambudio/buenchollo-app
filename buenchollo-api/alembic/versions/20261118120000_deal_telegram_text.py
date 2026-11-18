"""Borrador del post de Telegram en cada chollo (`deals.telegram_text`).

Se genera y edita desde «Editar chollo» en el admin; lo que se envía de verdad
sigue registrándose en `telegram_publications`.

Revision ID: 20261118120000
Revises: 20261108120000
"""

import sqlalchemy as sa
from alembic import op

revision = "20261118120000"
down_revision = "20261108120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("deals", sa.Column("telegram_text", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("deals", "telegram_text")
