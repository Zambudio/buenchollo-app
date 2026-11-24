"""Fuente `instagram` en la analítica first-party.

La bio de Instagram enlaza a `/instagram`, que redirige con
`utm_source=instagram`: esas visitas se cuentan aparte de «Otras webs».

Revision ID: 20261124120000
Revises: 20261122120000
"""

from alembic import op

revision = "20261124120000"
down_revision = "20261122120000"
branch_labels = None
depends_on = None

_NAME = "ck_analytics_events_source"


def upgrade() -> None:
    op.drop_constraint(_NAME, "analytics_events", type_="check")
    op.create_check_constraint(
        _NAME, "analytics_events", "source IN ('telegram', 'whatsapp', 'instagram', 'organic', 'referral', 'direct')"
    )


def downgrade() -> None:
    op.execute("UPDATE analytics_events SET source = 'referral' WHERE source = 'instagram'")
    op.drop_constraint(_NAME, "analytics_events", type_="check")
    op.create_check_constraint(
        _NAME, "analytics_events", "source IN ('telegram', 'whatsapp', 'organic', 'referral', 'direct')"
    )
