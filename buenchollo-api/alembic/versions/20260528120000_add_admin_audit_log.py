"""add admin_audit_log table

Primera migración Alembic real del proyecto tras la baseline
`20260527120000_baseline`. Crea la tabla `public.admin_audit_log` para
registrar acciones admin críticas con correlación al request_id.

Revision ID: 20260528120000_add_admin_audit_log
Revises: 20260527120000_baseline
Create Date: 2026-05-28
"""
import sqlalchemy as sa
from alembic import op

revision = "20260528120000_add_admin_audit_log"
down_revision = "20260527120000_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_audit_log",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=False),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=False),
            sa.ForeignKey("profiles.user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("target_type", sa.String(32), nullable=True),
        sa.Column("target_id", sa.String(64), nullable=True),
        sa.Column("payload", sa.JSON, nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_admin_audit_log_user_id", "admin_audit_log", ["user_id"])
    op.create_index("ix_admin_audit_log_action", "admin_audit_log", ["action"])
    op.create_index("ix_admin_audit_log_target_id", "admin_audit_log", ["target_id"])
    op.create_index("ix_admin_audit_log_created_at", "admin_audit_log", ["created_at"])

    # RLS: la tabla es interna del backend. El service_role bypassa RLS y
    # los endpoints admin son los únicos que la consultan, así que cerramos
    # completamente para anon/authenticated.
    op.execute("ALTER TABLE public.admin_audit_log ENABLE ROW LEVEL SECURITY;")


def downgrade() -> None:
    op.drop_index("ix_admin_audit_log_created_at", table_name="admin_audit_log")
    op.drop_index("ix_admin_audit_log_target_id", table_name="admin_audit_log")
    op.drop_index("ix_admin_audit_log_action", table_name="admin_audit_log")
    op.drop_index("ix_admin_audit_log_user_id", table_name="admin_audit_log")
    op.drop_table("admin_audit_log")
