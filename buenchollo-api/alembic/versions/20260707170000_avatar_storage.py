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
    op.execute(
        """
        INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
        VALUES (
          'avatars',
          'avatars',
          true,
          5242880,
          ARRAY['image/jpeg', 'image/png', 'image/webp', 'image/gif']
        )
        ON CONFLICT (id) DO UPDATE
        SET
          public = true,
          file_size_limit = 5242880,
          allowed_mime_types = ARRAY['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
        """
    )
    op.execute('DROP POLICY IF EXISTS "Avatars public read" ON storage.objects;')
    op.execute(
        """
        CREATE POLICY "Avatars public read" ON storage.objects
          FOR SELECT USING (bucket_id = 'avatars');
        """
    )
    op.execute('DROP POLICY IF EXISTS "Users upload own avatar" ON storage.objects;')
    op.execute(
        """
        CREATE POLICY "Users upload own avatar" ON storage.objects
          FOR INSERT TO authenticated
          WITH CHECK (
            bucket_id = 'avatars'
            AND (storage.foldername(name))[1] = auth.uid()::text
          );
        """
    )
    op.execute('DROP POLICY IF EXISTS "Users update own avatar" ON storage.objects;')
    op.execute(
        """
        CREATE POLICY "Users update own avatar" ON storage.objects
          FOR UPDATE TO authenticated
          USING (
            bucket_id = 'avatars'
            AND (storage.foldername(name))[1] = auth.uid()::text
          )
          WITH CHECK (
            bucket_id = 'avatars'
            AND (storage.foldername(name))[1] = auth.uid()::text
          );
        """
    )
    op.execute('DROP POLICY IF EXISTS "Users delete own avatar" ON storage.objects;')
    op.execute(
        """
        CREATE POLICY "Users delete own avatar" ON storage.objects
          FOR DELETE TO authenticated
          USING (
            bucket_id = 'avatars'
            AND (storage.foldername(name))[1] = auth.uid()::text
          );
        """
    )


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS "Users delete own avatar" ON storage.objects;')
    op.execute('DROP POLICY IF EXISTS "Users update own avatar" ON storage.objects;')
    op.execute('DROP POLICY IF EXISTS "Users upload own avatar" ON storage.objects;')
    op.execute('DROP POLICY IF EXISTS "Avatars public read" ON storage.objects;')
