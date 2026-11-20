"""Fuente `whatsapp` en la analítica first-party.

Las publicaciones del Canal de WhatsApp enlazan a `/whatsapp`, que redirige con
`utm_source=whatsapp`: esas visitas se cuentan aparte de «Otras webs».

Revision ID: 20261120130000
Revises: 20261120120000
"""

from alembic import op

revision = "20261120130000"
down_revision = "20261120120000"
branch_labels = None
depends_on = None

_NAME = "ck_analytics_events_source"


def upgrade() -> None:
    op.drop_constraint(_NAME, "analytics_events", type_="check")
    op.create_check_constraint(
        _NAME, "analytics_events", "source IN ('telegram', 'whatsapp', 'organic', 'referral', 'direct')"
    )


def downgrade() -> None:
    op.execute("UPDATE analytics_events SET source = 'referral' WHERE source = 'whatsapp'")
    op.drop_constraint(_NAME, "analytics_events", type_="check")
    op.create_check_constraint(
        _NAME, "analytics_events", "source IN ('telegram', 'organic', 'referral', 'direct')"
    )
