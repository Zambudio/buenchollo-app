"""create scheduled_tasks generic engine tables

Motor genérico de tareas programadas. Primera tarea: `price_check`
(revisión semanal de precios de chollos sin fecha de expiración).
`scheduled_task_run_items` NO tiene FK hacia deals/stores/categories:
es una foto histórica que debe sobrevivir aunque esas filas cambien o
se borren más tarde.

Revision ID: 20260809120000
Revises: 20260723170000
Create Date: 2026-08-09
"""
from alembic import op
import sqlalchemy as sa


revision = "20260809120000"
down_revision = "20260723170000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scheduled_tasks",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("task_type", sa.String(length=32), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("frequency_preset", sa.String(length=16), nullable=False, server_default="weekly"),
        sa.Column("run_hour", sa.SmallInteger(), nullable=False, server_default=sa.text("4")),
        sa.Column("config", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.execute("ALTER TABLE public.scheduled_tasks ENABLE ROW LEVEL SECURITY;")
    op.execute(
        """
        INSERT INTO scheduled_tasks (task_type, enabled, frequency_preset, run_hour, config)
        VALUES ('price_check', false, 'weekly', 4, '{"price_tolerance_percent": 10}'::json)
        """
    )

    op.create_table(
        "scheduled_task_runs",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("trigger_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_checked", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_affected", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("triggered_by", sa.Uuid(), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["scheduled_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["triggered_by"], ["profiles.user_id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_scheduled_task_runs_task_id_started_at",
        "scheduled_task_runs",
        ["task_id", "started_at"],
    )
    op.execute("ALTER TABLE public.scheduled_task_runs ENABLE ROW LEVEL SECURITY;")

    op.create_table(
        "scheduled_task_run_items",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("deal_id_snapshot", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("image_url", sa.String(length=2048), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("store_id", sa.Uuid(), nullable=True),
        sa.Column("store_name", sa.String(length=100), nullable=True),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("subcategory_id", sa.Uuid(), nullable=True),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.Column("affiliate_url", sa.String(length=2048), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("old_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("new_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("restored_deal_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["scheduled_task_runs.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_scheduled_task_run_items_run_id",
        "scheduled_task_run_items",
        ["run_id"],
    )
    op.execute("ALTER TABLE public.scheduled_task_run_items ENABLE ROW LEVEL SECURITY;")


def downgrade() -> None:
    op.drop_index("ix_scheduled_task_run_items_run_id", table_name="scheduled_task_run_items")
    op.drop_table("scheduled_task_run_items")
    op.drop_index("ix_scheduled_task_runs_task_id_started_at", table_name="scheduled_task_runs")
    op.drop_table("scheduled_task_runs")
    op.drop_table("scheduled_tasks")
