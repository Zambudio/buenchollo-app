"""improve Google profile defaults

Revision ID: 20260707154500
Revises: 20260530120000
Create Date: 2026-07-07
"""
from alembic import op

revision = "20260707154500"
down_revision = "20260530120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Supabase Auth trigger functions are managed through Supabase SQL
    # migrations, not through the app's Alembic connection. Running this from
    # the backend container can fail on function ownership and prevent startup.
    # Apply supabase/migrations/20260707154500_google_profile_metadata.sql from
    # the Supabase dashboard/CLI when changing the Auth trigger.
    pass


def downgrade() -> None:
    pass
