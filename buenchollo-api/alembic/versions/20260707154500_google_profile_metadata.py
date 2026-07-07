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
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.handle_new_user()
        RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
        BEGIN
          INSERT INTO public.profiles (user_id, display_name, avatar_url)
          VALUES (
            NEW.id,
            COALESCE(
              NEW.raw_user_meta_data->>'display_name',
              NEW.raw_user_meta_data->>'full_name',
              NEW.raw_user_meta_data->>'name',
              split_part(NEW.email, '@', 1)
            ),
            COALESCE(
              NEW.raw_user_meta_data->>'avatar_url',
              NEW.raw_user_meta_data->>'picture'
            )
          );
          INSERT INTO public.user_roles (user_id, role) VALUES (NEW.id, 'user');
          RETURN NEW;
        END;
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.handle_new_user()
        RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
        BEGIN
          INSERT INTO public.profiles (user_id, display_name, avatar_url)
          VALUES (
            NEW.id,
            COALESCE(
              NEW.raw_user_meta_data->>'display_name',
              NEW.raw_user_meta_data->>'full_name',
              split_part(NEW.email, '@', 1)
            ),
            NEW.raw_user_meta_data->>'avatar_url'
          );
          INSERT INTO public.user_roles (user_id, role) VALUES (NEW.id, 'user');
          RETURN NEW;
        END;
        $$;
        """
    )
