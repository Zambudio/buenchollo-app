"""Quita el aviso de afiliación genérico de los programas Awin / Tradedoubler.

La migración de redes (20261108120000) sembró en todos los programas el texto
«Enlace de afiliado: podemos recibir una comisión sin coste extra para ti.»
como «Aviso adicional del programa», y el post de Telegram lo añadía al final.
Ese aviso se había retirado de las publicaciones: solo se conserva el campo para
el programa que exija un texto propio. Se vacía únicamente donde sigue el texto
sembrado; uno escrito a mano no se toca.

Revision ID: 20261122120000
Revises: 20261120130000
"""

import sqlalchemy as sa
from alembic import op

revision = "20261122120000"
down_revision = "20261120130000"
branch_labels = None
depends_on = None

_DISCLOSURE = "Enlace de afiliado: podemos recibir una comisión sin coste extra para ti."


def upgrade() -> None:
    op.get_bind().execute(
        sa.text("UPDATE affiliate_programs SET disclosure_text = NULL WHERE disclosure_text = :text"),
        {"text": _DISCLOSURE},
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text("UPDATE affiliate_programs SET disclosure_text = :text WHERE disclosure_text IS NULL"),
        {"text": _DISCLOSURE},
    )
