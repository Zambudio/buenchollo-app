"""create avatars storage bucket

Revision ID: 20260707170000
Revises: 20260707154500
Create Date: 2026-07-07
"""
from alembic import op

revision = "20260707170000"
down_revision = "20260707154500"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Supabase Storage is a managed schema. Creating buckets/policies through
    # the app's Alembic connection can fail on permissions and stop the backend
    # container before Uvicorn starts. Apply
    # supabase/migrations/20260707170000_avatar_storage.sql from Supabase SQL
    # editor/CLI instead.
    pass


def downgrade() -> None:
    pass
