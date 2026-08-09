# Tareas programadas — Revisión de precios Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a generic "scheduled tasks" engine and its first task — a configurable weekly job that re-checks Amazon prices for published deals without an expiry date and deletes the ones that are no longer a valid offer, with a manual run-with-confirmation flow and a deletable/restorable execution log.

**Architecture:** New backend module `app/modules/scheduled_tasks/` (Clean Architecture: domain/application/infrastructure/api) with a registrable `TaskHandler` pattern so future task types can plug in without touching the scheduler or the run-log schema. One new APScheduler job polls hourly and self-checks which configured tasks are due. Frontend adds a new admin section that reuses existing patterns (`AlertDialog` for confirmations, react-query hooks like `useBlogAdmin.ts`, raw-HTML/Tailwind admin styling like `admin.blog.tsx`).

**Tech Stack:** FastAPI + SQLAlchemy async + Alembic + APScheduler (backend, `buenchollo-api/`); React + TanStack Router + TanStack Query + shadcn/Radix (frontend, `buenchollo-web/`).

## Global Constraints

- Backend: Python 3.11+, SQLAlchemy async with asyncpg, `Uuid(as_uuid=False)` for all id columns (per `CLAUDE.md`).
- No docstrings/comments on untouched code; add comments only for non-obvious constraints.
- Routers contain no business logic — it lives in `application/`. External integrations (Amazon) live in `infrastructure/`.
- Every admin-destructive action gets an `audit_log(...)` call (see `app/core/audit/service.py`).
- Tests: unit tests mock the session/repos (no real DB) for pure logic and query-shape checks; integration tests (`pytest.mark.integration`) hit real Postgres via the `integration_client` fixture — mirror existing files, don't invent a third style.
- Frontend: mobile-first, fully responsive, no horizontal overflow (per `CLAUDE.md` §5). Follow the existing "surface-800/900, font-mono uppercase, cyan-glow accent" dark theme used across `admin.tsx` / `admin.blog.tsx` / `AdminDealsTable.tsx`.
- Never call `git push`, never touch `main` — this repo works on `develop` (per `CLAUDE.md`), but this plan does not include any commit/push instructions beyond the standard `git commit` step at the end of each task; branch/PR handling is left to the user.

---

## Backend

### Task 1: Migration + SQLAlchemy domain models for the 3 new tables

**Files:**
- Create: `buenchollo-api/alembic/versions/20260809120000_scheduled_tasks.py`
- Create: `buenchollo-api/app/modules/scheduled_tasks/__init__.py`
- Create: `buenchollo-api/app/modules/scheduled_tasks/domain/__init__.py`
- Create: `buenchollo-api/app/modules/scheduled_tasks/domain/models.py`
- Test: `buenchollo-api/app/tests/test_scheduled_tasks_models.py`

**Interfaces:**
- Produces: `ScheduledTask`, `ScheduledTaskRun`, `ScheduledTaskRunItem` SQLAlchemy models in `app.modules.scheduled_tasks.domain.models`, tables `scheduled_tasks` / `scheduled_task_runs` / `scheduled_task_run_items`. `ScheduledTaskRun.items` is a `relationship` to `ScheduledTaskRunItem` with `cascade="all, delete-orphan"`.

- [ ] **Step 1: Write the migration**

Create `buenchollo-api/alembic/versions/20260809120000_scheduled_tasks.py`:

```python
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
```

- [ ] **Step 2: Apply the migration locally**

Run: `cd buenchollo-api && alembic upgrade head`
Expected: no errors, `scheduled_tasks` has exactly one row (`task_type='price_check'`, `enabled=false`).

- [ ] **Step 3: Write the domain models**

Create `buenchollo-api/app/modules/scheduled_tasks/__init__.py` (empty file).
Create `buenchollo-api/app/modules/scheduled_tasks/domain/__init__.py` (empty file).

Create `buenchollo-api/app/modules/scheduled_tasks/domain/models.py`:

```python
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    SmallInteger,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

import app.modules.users.domain.models  # noqa: F401


class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_type: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    frequency_preset: Mapped[str] = mapped_column(String(16), default="weekly", nullable=False)
    run_hour: Mapped[int] = mapped_column(SmallInteger, default=4, nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )


class ScheduledTaskRun(Base):
    __tablename__ = "scheduled_task_runs"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(
        ForeignKey("scheduled_tasks.id", ondelete="CASCADE"), type_=Uuid(as_uuid=False), nullable=False
    )
    trigger_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_checked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_affected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    triggered_by: Mapped[str | None] = mapped_column(
        ForeignKey("profiles.user_id", ondelete="SET NULL"), type_=Uuid(as_uuid=False), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    items: Mapped[list["ScheduledTaskRunItem"]] = relationship(
        "ScheduledTaskRunItem", cascade="all, delete-orphan", back_populates="run"
    )


class ScheduledTaskRunItem(Base):
    __tablename__ = "scheduled_task_run_items"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(
        ForeignKey("scheduled_task_runs.id", ondelete="CASCADE"), type_=Uuid(as_uuid=False), nullable=False
    )
    deal_id_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    store_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    store_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    subcategory_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    affiliate_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    old_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    new_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    restored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    restored_deal_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc)
    )

    run: Mapped["ScheduledTaskRun"] = relationship("ScheduledTaskRun", back_populates="items")
```

- [ ] **Step 4: Write the mapper-resolution test**

Create `buenchollo-api/app/tests/test_scheduled_tasks_models.py`:

```python
"""Verifica que los modelos de scheduled_tasks resuelven sus relaciones
(FK a profiles) en un proceso aislado, igual que scheduled_deals
(test_scheduler_builder.py::test_repositorio_programado_resuelve_mappers_en_proceso_aislado)."""
import subprocess
import sys


def test_scheduled_tasks_resuelve_mappers_en_proceso_aislado():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from app.modules.scheduled_tasks.domain.models import ScheduledTask, ScheduledTaskRun, ScheduledTaskRunItem; "
                "from sqlalchemy import inspect; "
                "inspect(ScheduledTask); inspect(ScheduledTaskRun); inspect(ScheduledTaskRunItem)"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_tablenames():
    from app.modules.scheduled_tasks.domain.models import (
        ScheduledTask,
        ScheduledTaskRun,
        ScheduledTaskRunItem,
    )

    assert ScheduledTask.__tablename__ == "scheduled_tasks"
    assert ScheduledTaskRun.__tablename__ == "scheduled_task_runs"
    assert ScheduledTaskRunItem.__tablename__ == "scheduled_task_run_items"
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd buenchollo-api && pytest app/tests/test_scheduled_tasks_models.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add buenchollo-api/alembic/versions/20260809120000_scheduled_tasks.py buenchollo-api/app/modules/scheduled_tasks/__init__.py buenchollo-api/app/modules/scheduled_tasks/domain/ buenchollo-api/app/tests/test_scheduled_tasks_models.py
git commit -m "feat: add scheduled_tasks tables and domain models"
```

---

### Task 2: `DealRepository.get_active_without_expiry_with_asin()`

**Files:**
- Modify: `buenchollo-api/app/modules/deals/infrastructure/repository.py`
- Test: `buenchollo-api/app/tests/test_deal_filters.py`

**Interfaces:**
- Consumes: `Deal` model fields `status`, `expires_at`, `external_id` (`app/modules/deals/domain/models.py`).
- Produces: `DealRepository.get_active_without_expiry_with_asin(self) -> list[Deal]`, used by Task 5's `PriceCheckHandler` via `ScheduledTaskService`.

- [ ] **Step 1: Write the failing unit test**

Append to `buenchollo-api/app/tests/test_deal_filters.py`:

```python
@pytest.mark.asyncio
async def test_get_active_without_expiry_with_asin_filters_correctly():
    result = Mock()
    result.scalars.return_value.all.return_value = []
    session = Mock()
    session.execute = AsyncMock(return_value=result)

    repo = DealRepository(session)
    await repo.get_active_without_expiry_with_asin()

    statement = session.execute.await_args.args[0]
    sql = str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert "deals.status = 'active'" in sql
    assert "deals.expires_at IS NULL" in sql
    assert "deals.external_id IS NOT NULL" in sql
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd buenchollo-api && pytest app/tests/test_deal_filters.py::test_get_active_without_expiry_with_asin_filters_correctly -v`
Expected: FAIL with `AttributeError: 'DealRepository' object has no attribute 'get_active_without_expiry_with_asin'`.

- [ ] **Step 3: Implement the method**

In `buenchollo-api/app/modules/deals/infrastructure/repository.py`, add after `get_due_scheduled` (after line 255):

```python
    async def get_active_without_expiry_with_asin(self) -> list[Deal]:
        """Chollos activos sin fecha de expiración y con ASIN — candidatos de
        la tarea programada de revisión de precios. Usa `_base_deal_query()`
        (eager-loads category/subcategory/store) porque el caller evalúa
        estos deals dentro de un threadpool y no puede lazy-load relaciones
        ahí (el AsyncSession vive en el hilo del event loop, no en ese hilo)."""
        result = await self.session.execute(
            self._base_deal_query()
            .where(Deal.status == "active")
            .where(Deal.expires_at.is_(None))
            .where(Deal.external_id.isnot(None))
        )
        return list(result.scalars().all())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd buenchollo-api && pytest app/tests/test_deal_filters.py -v`
Expected: all pass, including the new test.

- [ ] **Step 5: Commit**

```bash
git add buenchollo-api/app/modules/deals/infrastructure/repository.py buenchollo-api/app/tests/test_deal_filters.py
git commit -m "feat: add DealRepository.get_active_without_expiry_with_asin"
```

---

### Task 3: `ScheduledTaskRepository`

**Files:**
- Create: `buenchollo-api/app/modules/scheduled_tasks/infrastructure/__init__.py`
- Create: `buenchollo-api/app/modules/scheduled_tasks/infrastructure/repository.py`
- Test: `buenchollo-api/app/tests/test_scheduled_tasks_repository.py`

**Interfaces:**
- Consumes: `ScheduledTask`, `ScheduledTaskRun`, `ScheduledTaskRunItem` from Task 1.
- Produces: `ScheduledTaskRepository` with methods `get_by_id`, `list_tasks`, `get_enabled_tasks`, `update_task`, `create_run`, `list_runs`, `get_run_by_id`, `delete_run`, `delete_runs_by_ids`, `get_run_item_by_id`, `update_run_item` — used by Task 5/6 (`ScheduledTaskService`) and Task 7 (scheduler).

- [ ] **Step 1: Write the failing unit tests (query shape)**

Create `buenchollo-api/app/modules/scheduled_tasks/infrastructure/__init__.py` (empty file).

Create `buenchollo-api/app/tests/test_scheduled_tasks_repository.py`:

```python
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.dialects import postgresql

from app.modules.scheduled_tasks.infrastructure.repository import ScheduledTaskRepository


def _repo_with_mocked_session():
    result = Mock()
    result.scalars.return_value.all.return_value = []
    result.scalars.return_value.first.return_value = None
    session = Mock()
    session.execute = AsyncMock(return_value=result)
    return ScheduledTaskRepository(session), session


def _compiled_sql(session) -> str:
    statement = session.execute.await_args.args[0]
    return str(
        statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )


@pytest.mark.asyncio
async def test_get_enabled_tasks_filters_by_enabled():
    repo, session = _repo_with_mocked_session()

    await repo.get_enabled_tasks()

    sql = _compiled_sql(session)
    assert "scheduled_tasks.enabled = true" in sql


@pytest.mark.asyncio
async def test_get_by_id_filters_by_id():
    repo, session = _repo_with_mocked_session()

    await repo.get_by_id("task-1")

    sql = _compiled_sql(session)
    assert "scheduled_tasks.id = 'task-1'" in sql


@pytest.mark.asyncio
async def test_list_runs_filters_by_task_and_orders_recent_first():
    repo, session = _repo_with_mocked_session()

    await repo.list_runs("task-1", limit=50, offset=0)

    sql = _compiled_sql(session)
    assert "scheduled_task_runs.task_id = 'task-1'" in sql
    assert "ORDER BY scheduled_task_runs.started_at DESC" in sql
    assert "LIMIT 50" in sql
```

Note: `get_run_by_id`'s `selectinload(ScheduledTaskRun.items)` is deliberately NOT unit-tested here — `selectinload` runs as a second query and doesn't appear in the compiled SQL of the first, so asserting on it would mean relying on SQLAlchemy's private `Select._with_options` internals (fragile, not documented API). Task 9's integration test `test_get_run_detail_incluye_los_items` exercises this for real against Postgres and would fail with `MissingGreenlet` if the eager load were missing — that's the meaningful coverage for this behavior.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd buenchollo-api && pytest app/tests/test_scheduled_tasks_repository.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.modules.scheduled_tasks.infrastructure.repository'`.

- [ ] **Step 3: Implement the repository**

Create `buenchollo-api/app/modules/scheduled_tasks/infrastructure/repository.py`:

```python
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.scheduled_tasks.domain.models import (
    ScheduledTask,
    ScheduledTaskRun,
    ScheduledTaskRunItem,
)


class ScheduledTaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # --- ScheduledTask (config) ---

    async def get_by_id(self, task_id: str) -> ScheduledTask | None:
        result = await self.session.execute(select(ScheduledTask).where(ScheduledTask.id == task_id))
        return result.scalars().first()

    async def list_tasks(self) -> list[ScheduledTask]:
        result = await self.session.execute(select(ScheduledTask).order_by(ScheduledTask.task_type))
        return list(result.scalars().all())

    async def get_enabled_tasks(self) -> list[ScheduledTask]:
        result = await self.session.execute(select(ScheduledTask).where(ScheduledTask.enabled.is_(True)))
        return list(result.scalars().all())

    async def update_task(self, task: ScheduledTask) -> ScheduledTask:
        await self.session.flush()
        return task

    # --- ScheduledTaskRun ---

    async def create_run(self, run: ScheduledTaskRun) -> ScheduledTaskRun:
        self.session.add(run)
        await self.session.flush()
        return run

    async def list_runs(self, task_id: str, limit: int = 50, offset: int = 0) -> list[ScheduledTaskRun]:
        result = await self.session.execute(
            select(ScheduledTaskRun)
            .where(ScheduledTaskRun.task_id == task_id)
            .order_by(ScheduledTaskRun.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_run_by_id(self, run_id: str) -> ScheduledTaskRun | None:
        result = await self.session.execute(
            select(ScheduledTaskRun)
            .options(selectinload(ScheduledTaskRun.items))
            .where(ScheduledTaskRun.id == run_id)
        )
        return result.scalars().first()

    async def delete_run(self, run: ScheduledTaskRun) -> None:
        await self.session.delete(run)
        await self.session.flush()

    async def delete_runs_by_ids(self, run_ids: list[str]) -> int:
        if not run_ids:
            return 0
        result = await self.session.execute(
            delete(ScheduledTaskRun).where(ScheduledTaskRun.id.in_(run_ids))
        )
        await self.session.flush()
        return result.rowcount or 0

    # --- ScheduledTaskRunItem ---

    async def get_run_item_by_id(self, item_id: str) -> ScheduledTaskRunItem | None:
        result = await self.session.execute(
            select(ScheduledTaskRunItem).where(ScheduledTaskRunItem.id == item_id)
        )
        return result.scalars().first()

    async def update_run_item(self, item: ScheduledTaskRunItem) -> ScheduledTaskRunItem:
        await self.session.flush()
        return item
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd buenchollo-api && pytest app/tests/test_scheduled_tasks_repository.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add buenchollo-api/app/modules/scheduled_tasks/infrastructure/ buenchollo-api/app/tests/test_scheduled_tasks_repository.py
git commit -m "feat: add ScheduledTaskRepository"
```

---

### Task 4: `PriceCheckHandler` (evaluation + deletion logic)

**Files:**
- Create: `buenchollo-api/app/modules/scheduled_tasks/application/__init__.py`
- Create: `buenchollo-api/app/modules/scheduled_tasks/application/task_handler.py`
- Create: `buenchollo-api/app/modules/scheduled_tasks/application/price_check_handler.py`
- Test: `buenchollo-api/app/tests/test_price_check_handler.py`

**Interfaces:**
- Consumes: `ProductPreview` (`app/modules/products/domain/entities.py`), `Deal` (`app/modules/deals/domain/models.py`), `DealRepository.get_by_id` / `.delete` (`app/modules/deals/infrastructure/repository.py`).
- Produces:
  - `Candidate` dataclass (`deal_id, title, slug, image_url, description, store_id, store_name, category_id, subcategory_id, external_id, affiliate_url, source_url, old_price: Decimal, new_price: Decimal | None, reason: str`) — consumed by Task 5/6/8/9.
  - `PreviewResult` dataclass (`total_checked: int, candidates: list[Candidate]`) — consumed by Task 5/8.
  - `ProductVerifier` Protocol (`get_product_preview(asin: str) -> ProductPreview | None`).
  - `PriceCheckHandler(product_verifier: ProductVerifier, deal_repo: DealRepository)` with `evaluate(self, deals: list[Deal], config: dict) -> PreviewResult` (sync) and `async execute(self, candidates: list[Candidate]) -> list[Candidate]` (returns the subset actually deleted).

- [ ] **Step 1: Write the failing unit tests**

Create `buenchollo-api/app/modules/scheduled_tasks/application/__init__.py` (empty file).

Create `buenchollo-api/app/tests/test_price_check_handler.py`:

```python
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.products.domain.entities import ProductPreview
from app.modules.scheduled_tasks.application.price_check_handler import PriceCheckHandler


def _deal(**overrides):
    base = dict(
        id="deal-1",
        title="Producto X",
        slug="producto-x",
        image_url="https://img/x.jpg",
        description="desc",
        store_id="store-1",
        store=SimpleNamespace(name="Amazon"),
        category_id="cat-1",
        subcategory_id=None,
        external_id="B0D9WH9WLD",
        affiliate_url="https://amazon.es/dp/B0D9WH9WLD",
        source_url=None,
        current_price=100.0,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class FakeVerifier:
    def __init__(self, products: dict[str, ProductPreview | None]):
        self.products = products

    def get_product_preview(self, asin: str):
        return self.products.get(asin)


class FakeDealRepo:
    def __init__(self, deals_by_id: dict[str, object]):
        self.deals_by_id = deals_by_id
        self.deleted: list[str] = []
        self.get_by_id = AsyncMock(side_effect=lambda deal_id: self.deals_by_id.get(deal_id))

    async def delete(self, deal):
        self.deleted.append(deal.id)


def test_evaluate_marca_price_increase_fuera_de_tolerancia():
    deal = _deal()
    verifier = FakeVerifier({"B0D9WH9WLD": ProductPreview(
        current_price=115.0, original_price=150.0, discount_percentage=23, in_stock=True,
    )})
    handler = PriceCheckHandler(verifier, FakeDealRepo({}))

    result = handler.evaluate([deal], {"price_tolerance_percent": 10})

    assert result.total_checked == 1
    assert len(result.candidates) == 1
    assert result.candidates[0].reason == "price_increase"
    assert result.candidates[0].new_price == 115.0


def test_evaluate_no_marca_price_increase_dentro_de_tolerancia():
    deal = _deal()
    verifier = FakeVerifier({"B0D9WH9WLD": ProductPreview(
        current_price=108.0, original_price=150.0, discount_percentage=28, in_stock=True,
    )})
    handler = PriceCheckHandler(verifier, FakeDealRepo({}))

    result = handler.evaluate([deal], {"price_tolerance_percent": 10})

    assert result.total_checked == 1
    assert result.candidates == []


def test_evaluate_marca_out_of_stock():
    deal = _deal()
    verifier = FakeVerifier({"B0D9WH9WLD": ProductPreview(
        current_price=90.0, original_price=150.0, discount_percentage=40, in_stock=False,
    )})
    handler = PriceCheckHandler(verifier, FakeDealRepo({}))

    result = handler.evaluate([deal], {"price_tolerance_percent": 10})

    assert len(result.candidates) == 1
    assert result.candidates[0].reason == "out_of_stock"
    assert result.candidates[0].new_price is None


def test_evaluate_marca_no_longer_deal_si_amazon_ya_no_reporta_descuento():
    deal = _deal()
    verifier = FakeVerifier({"B0D9WH9WLD": ProductPreview(
        current_price=100.0, original_price=None, discount_percentage=None, in_stock=True,
    )})
    handler = PriceCheckHandler(verifier, FakeDealRepo({}))

    result = handler.evaluate([deal], {"price_tolerance_percent": 10})

    assert len(result.candidates) == 1
    assert result.candidates[0].reason == "no_longer_deal"


def test_evaluate_ignora_asin_no_encontrado_en_amazon():
    deal = _deal()
    verifier = FakeVerifier({})  # Amazon no devuelve nada para este ASIN
    handler = PriceCheckHandler(verifier, FakeDealRepo({}))

    result = handler.evaluate([deal], {"price_tolerance_percent": 10})

    assert result.total_checked == 1
    assert result.candidates == []


def test_evaluate_usa_tolerancia_por_defecto_diez_por_ciento_si_falta_config():
    deal = _deal()
    verifier = FakeVerifier({"B0D9WH9WLD": ProductPreview(
        current_price=111.0, original_price=150.0, discount_percentage=26, in_stock=True,
    )})
    handler = PriceCheckHandler(verifier, FakeDealRepo({}))

    result = handler.evaluate([deal], {})

    assert len(result.candidates) == 1
    assert result.candidates[0].reason == "price_increase"


@pytest.mark.asyncio
async def test_execute_borra_los_deals_encontrados_y_omite_los_ya_borrados():
    from app.modules.scheduled_tasks.application.task_handler import Candidate
    from decimal import Decimal

    deal1 = _deal(id="deal-1")
    repo = FakeDealRepo({"deal-1": deal1})  # deal-2 ya no existe (borrado por otra vía)
    handler = PriceCheckHandler(FakeVerifier({}), repo)
    candidates = [
        Candidate(
            deal_id="deal-1", title="X", slug="x", image_url=None, description=None,
            store_id=None, store_name=None, category_id=None, subcategory_id=None,
            external_id="B0D9WH9WLD", affiliate_url="https://a", source_url=None,
            old_price=Decimal("100.00"), new_price=Decimal("115.00"), reason="price_increase",
        ),
        Candidate(
            deal_id="deal-2", title="Y", slug="y", image_url=None, description=None,
            store_id=None, store_name=None, category_id=None, subcategory_id=None,
            external_id="B0OTHER0001", affiliate_url="https://b", source_url=None,
            old_price=Decimal("50.00"), new_price=None, reason="out_of_stock",
        ),
    ]

    deleted = await handler.execute(candidates)

    assert [c.deal_id for c in deleted] == ["deal-1"]
    assert repo.deleted == ["deal-1"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd buenchollo-api && pytest app/tests/test_price_check_handler.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.modules.scheduled_tasks.application.price_check_handler'`.

- [ ] **Step 3: Write `task_handler.py` (shared dataclasses + Protocol)**

Create `buenchollo-api/app/modules/scheduled_tasks/application/task_handler.py`:

```python
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.modules.products.domain.entities import ProductPreview


@dataclass
class Candidate:
    deal_id: str
    title: str
    slug: str
    image_url: str | None
    description: str | None
    store_id: str | None
    store_name: str | None
    category_id: str | None
    subcategory_id: str | None
    external_id: str
    affiliate_url: str
    source_url: str | None
    old_price: Decimal
    new_price: Decimal | None
    reason: str


@dataclass
class PreviewResult:
    total_checked: int
    candidates: list[Candidate]


class ProductVerifier(Protocol):
    def get_product_preview(self, asin: str) -> ProductPreview | None: ...


class TaskHandler(Protocol):
    def evaluate(self, deals: list, config: dict) -> PreviewResult: ...
    async def execute(self, candidates: list[Candidate]) -> list[Candidate]: ...
```

- [ ] **Step 4: Write `price_check_handler.py`**

Create `buenchollo-api/app/modules/scheduled_tasks/application/price_check_handler.py`:

```python
import logging
from decimal import Decimal, ROUND_HALF_UP

from app.modules.scheduled_tasks.application.task_handler import (
    Candidate,
    PreviewResult,
    ProductVerifier,
)

logger = logging.getLogger(__name__)

_DEFAULT_TOLERANCE_PERCENT = 10


class PriceCheckHandler:
    def __init__(self, product_verifier: ProductVerifier, deal_repo):
        self.product_verifier = product_verifier
        self.deal_repo = deal_repo

    def evaluate(self, deals: list, config: dict) -> PreviewResult:
        tolerance = Decimal(str(config.get("price_tolerance_percent", _DEFAULT_TOLERANCE_PERCENT)))
        candidates: list[Candidate] = []
        for deal in deals:
            product = self.product_verifier.get_product_preview(deal.external_id)
            if product is None:
                continue
            reason = self._evaluate_one(deal, product, tolerance)
            if reason is None:
                continue
            candidates.append(self._to_candidate(deal, product, reason))
        return PreviewResult(total_checked=len(deals), candidates=candidates)

    @staticmethod
    def _evaluate_one(deal, product, tolerance: Decimal) -> str | None:
        if not product.in_stock:
            return "out_of_stock"
        if product.original_price is None or product.discount_percentage is None:
            return "no_longer_deal"
        if product.current_price is None:
            return None
        old_price = Decimal(str(deal.current_price))
        current_price = Decimal(str(product.current_price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        maximum_price = old_price * (Decimal("1") + tolerance / Decimal("100"))
        if current_price > maximum_price:
            return "price_increase"
        return None

    @staticmethod
    def _to_candidate(deal, product, reason: str) -> Candidate:
        new_price = None
        if reason == "price_increase":
            new_price = Decimal(str(product.current_price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return Candidate(
            deal_id=deal.id,
            title=deal.title,
            slug=deal.slug,
            image_url=deal.image_url,
            description=deal.description,
            store_id=deal.store_id,
            store_name=deal.store.name if deal.store else None,
            category_id=deal.category_id,
            subcategory_id=deal.subcategory_id,
            external_id=deal.external_id,
            affiliate_url=deal.affiliate_url,
            source_url=deal.source_url,
            old_price=Decimal(str(deal.current_price)),
            new_price=new_price,
            reason=reason,
        )

    async def execute(self, candidates: list[Candidate]) -> list[Candidate]:
        deleted: list[Candidate] = []
        for candidate in candidates:
            deal = await self.deal_repo.get_by_id(candidate.deal_id)
            if deal is None:
                continue
            await self.deal_repo.delete(deal)
            deleted.append(candidate)
        return deleted
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd buenchollo-api && pytest app/tests/test_price_check_handler.py -v`
Expected: 7 passed.

- [ ] **Step 6: Commit**

```bash
git add buenchollo-api/app/modules/scheduled_tasks/application/__init__.py buenchollo-api/app/modules/scheduled_tasks/application/task_handler.py buenchollo-api/app/modules/scheduled_tasks/application/price_check_handler.py buenchollo-api/app/tests/test_price_check_handler.py
git commit -m "feat: add PriceCheckHandler evaluation and deletion logic"
```

---

### Task 5: `ScheduledTaskService` — config, preview, confirm, automatic run

**Files:**
- Create: `buenchollo-api/app/modules/scheduled_tasks/domain/exceptions.py`
- Create: `buenchollo-api/app/modules/scheduled_tasks/application/scheduled_task_service.py`
- Test: `buenchollo-api/app/tests/test_scheduled_task_service.py`

**Interfaces:**
- Consumes: `ScheduledTaskRepository` (Task 3), `DealRepository` (Task 2, plus existing `get_by_id`/`delete`), `TaskHandler`/`Candidate`/`PreviewResult` (Task 4), `audit_log` (`app/core/audit/service.py`).
- Produces:
  - `ScheduledTaskNotFound(NotFoundError)` in `app.modules.scheduled_tasks.domain.exceptions`.
  - `FREQUENCY_DAYS: dict[str, int]` and `is_task_due(task: ScheduledTask, now: datetime) -> bool` in `scheduled_task_service.py` — consumed by Task 7 (scheduler).
  - `ScheduledTaskService(repo, deal_repo, handlers: dict[str, TaskHandler], session)` with `async list_tasks()`, `async update_config(task_id, **fields)`, `async preview(task_id) -> PreviewResult`, `async confirm(task_id, total_checked, candidates, triggered_by) -> ScheduledTaskRun`, `async run_automatic(task_id) -> ScheduledTaskRun` — consumed by Task 6 (extended with more methods), Task 7 (scheduler), Task 8/9 (API).

- [ ] **Step 1: Write the failing unit tests**

Create `buenchollo-api/app/tests/test_scheduled_task_service.py`:

```python
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.scheduled_tasks.application.scheduled_task_service import (
    FREQUENCY_DAYS,
    ScheduledTaskService,
    is_task_due,
)
from app.modules.scheduled_tasks.application.task_handler import Candidate, PreviewResult
from app.modules.scheduled_tasks.domain.exceptions import ScheduledTaskNotFound


def _task(**overrides):
    base = dict(
        id="task-1",
        task_type="price_check",
        enabled=True,
        frequency_preset="weekly",
        run_hour=4,
        config={"price_tolerance_percent": 10},
        last_run_at=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _candidate(**overrides):
    base = dict(
        deal_id="deal-1", title="X", slug="x", image_url=None, description=None,
        store_id=None, store_name=None, category_id=None, subcategory_id=None,
        external_id="B0D9WH9WLD", affiliate_url="https://a", source_url=None,
        old_price=Decimal("100.00"), new_price=Decimal("115.00"), reason="price_increase",
    )
    base.update(overrides)
    return Candidate(**base)


def _build_service(task, handler):
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=task)
    repo.update_task = AsyncMock(side_effect=lambda t: t)
    repo.create_run = AsyncMock(side_effect=lambda run: run)
    deal_repo = MagicMock()
    deal_repo.get_active_without_expiry_with_asin = AsyncMock(return_value=["deal-obj"])
    session = MagicMock()
    session.begin_nested = MagicMock(return_value=_NoopAsyncCtx())
    session.add = MagicMock()
    session.flush = AsyncMock()
    service = ScheduledTaskService(repo, deal_repo, {"price_check": handler}, session)
    return service, repo, deal_repo


class _NoopAsyncCtx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


# --- is_task_due ---

def test_is_task_due_false_si_deshabilitada():
    task = _task(enabled=False)
    assert is_task_due(task, datetime(2026, 8, 10, 5, tzinfo=timezone.utc)) is False


def test_is_task_due_false_antes_de_run_hour():
    task = _task(run_hour=4)
    assert is_task_due(task, datetime(2026, 8, 10, 3, 0, tzinfo=timezone.utc)) is False


def test_is_task_due_true_primera_vez_tras_run_hour():
    task = _task(run_hour=4, last_run_at=None)
    assert is_task_due(task, datetime(2026, 8, 10, 5, 0, tzinfo=timezone.utc)) is True


def test_is_task_due_false_si_no_han_pasado_los_dias_de_frecuencia():
    last_run = datetime(2026, 8, 5, 5, 0, tzinfo=timezone.utc)
    task = _task(frequency_preset="weekly", run_hour=4, last_run_at=last_run)
    now = last_run + timedelta(days=3)
    assert is_task_due(task, now) is False


def test_is_task_due_true_si_ya_paso_el_intervalo_de_frecuencia():
    last_run = datetime(2026, 8, 1, 5, 0, tzinfo=timezone.utc)
    task = _task(frequency_preset="weekly", run_hour=4, last_run_at=last_run)
    now = last_run + timedelta(days=FREQUENCY_DAYS["weekly"])
    assert is_task_due(task, now) is True


# --- preview ---

@pytest.mark.asyncio
async def test_preview_delega_en_el_handler_con_los_deals_y_config_de_la_tarea():
    task = _task()
    handler = MagicMock()
    handler.evaluate = MagicMock(return_value=PreviewResult(total_checked=1, candidates=[]))
    service, repo, deal_repo = _build_service(task, handler)

    result = await service.preview("task-1")

    deal_repo.get_active_without_expiry_with_asin.assert_awaited_once()
    handler.evaluate.assert_called_once_with(["deal-obj"], task.config)
    assert result.total_checked == 1


@pytest.mark.asyncio
async def test_preview_lanza_not_found_si_la_tarea_no_existe():
    handler = MagicMock()
    service, repo, _ = _build_service(_task(), handler)
    repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(ScheduledTaskNotFound):
        await service.preview("no-existe")


# --- confirm ---

@pytest.mark.asyncio
async def test_confirm_borra_persiste_el_run_y_actualiza_last_run_at():
    task = _task(last_run_at=None)
    handler = MagicMock()
    candidate = _candidate()
    handler.execute = AsyncMock(return_value=[candidate])
    service, repo, _ = _build_service(task, handler)

    run = await service.confirm("task-1", total_checked=5, candidates=[candidate], triggered_by="admin-1")

    handler.execute.assert_awaited_once_with([candidate])
    assert run.trigger_type == "manual"
    assert run.status == "completed"
    assert run.total_checked == 5
    assert run.total_affected == 1
    assert run.triggered_by == "admin-1"
    assert len(run.items) == 1
    assert run.items[0].deal_id_snapshot == "deal-1"
    assert run.items[0].reason == "price_increase"
    assert task.last_run_at is not None
    repo.update_task.assert_awaited_once_with(task)


# --- run_automatic ---

@pytest.mark.asyncio
async def test_run_automatic_ejecuta_preview_y_execute_y_marca_automatic():
    task = _task(last_run_at=None)
    handler = MagicMock()
    candidate = _candidate()
    handler.evaluate = MagicMock(return_value=PreviewResult(total_checked=3, candidates=[candidate]))
    handler.execute = AsyncMock(return_value=[candidate])
    service, repo, deal_repo = _build_service(task, handler)

    run = await service.run_automatic("task-1")

    assert run.trigger_type == "automatic"
    assert run.status == "completed"
    assert run.triggered_by is None
    assert run.total_checked == 3
    assert run.total_affected == 1
    assert task.last_run_at is not None


@pytest.mark.asyncio
async def test_run_automatic_persiste_run_fallido_y_relanza_si_el_handler_explota():
    task = _task(last_run_at=None)
    handler = MagicMock()
    handler.evaluate = MagicMock(side_effect=RuntimeError("Amazon caído"))
    service, repo, _ = _build_service(task, handler)

    with pytest.raises(RuntimeError):
        await service.run_automatic("task-1")

    created_run = repo.create_run.await_args.args[0]
    assert created_run.status == "failed"
    assert "Amazon caído" in created_run.error_message
    assert task.last_run_at is None  # no se actualiza en fallo: reintenta en el próximo tick
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd buenchollo-api && pytest app/tests/test_scheduled_task_service.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write domain exceptions**

Create `buenchollo-api/app/modules/scheduled_tasks/domain/exceptions.py`:

```python
"""Excepciones de dominio del módulo scheduled_tasks."""
from app.core.exceptions import ConflictError, NotFoundError


class ScheduledTaskNotFound(NotFoundError):
    def __init__(self, task_id: str | None = None):
        super().__init__(
            f"Tarea programada '{task_id}' no encontrada" if task_id else "Tarea programada no encontrada"
        )


class ScheduledTaskRunNotFound(NotFoundError):
    def __init__(self, run_id: str):
        super().__init__(f"Registro de ejecución '{run_id}' no encontrado")


class RunItemNotFound(NotFoundError):
    def __init__(self, item_id: str):
        super().__init__(f"Elemento de registro '{item_id}' no encontrado")


class ItemAlreadyRestoredError(ConflictError):
    def __init__(self, item_id: str):
        super().__init__(f"El elemento '{item_id}' ya fue restaurado")


class RestoreFailedError(ConflictError):
    def __init__(self, item_id: str):
        super().__init__(
            f"No se pudo restaurar el elemento '{item_id}': "
            "la tienda o categoría original ya no existe"
        )
```

- [ ] **Step 4: Write the service**

Create `buenchollo-api/app/modules/scheduled_tasks/application/scheduled_task_service.py`:

```python
import logging
from datetime import datetime, timedelta, timezone

from starlette.concurrency import run_in_threadpool

from app.core.audit import audit_log
from app.modules.scheduled_tasks.application.task_handler import Candidate, PreviewResult, TaskHandler
from app.modules.scheduled_tasks.domain.exceptions import ScheduledTaskNotFound
from app.modules.scheduled_tasks.domain.models import ScheduledTask, ScheduledTaskRun, ScheduledTaskRunItem

logger = logging.getLogger(__name__)

FREQUENCY_DAYS = {"daily": 1, "weekly": 7, "biweekly": 14, "monthly": 30}


def is_task_due(task: ScheduledTask, now: datetime) -> bool:
    """`now` debe representar ya la hora local del servidor (el caller hace
    la conversión desde UTC, ver scheduler.py) — aquí se compara tal cual,
    para que el test no dependa de la zona horaria de la máquina que lo
    ejecuta."""
    if not task.enabled:
        return False
    if now.hour < task.run_hour:
        return False
    if task.last_run_at is None:
        return True
    days = FREQUENCY_DAYS[task.frequency_preset]
    return now >= task.last_run_at + timedelta(days=days)


class ScheduledTaskService:
    def __init__(self, repo, deal_repo, handlers: dict[str, TaskHandler], session):
        self.repo = repo
        self.deal_repo = deal_repo
        self.handlers = handlers
        self.session = session

    async def _get_task_or_404(self, task_id: str) -> ScheduledTask:
        task = await self.repo.get_by_id(task_id)
        if task is None:
            raise ScheduledTaskNotFound(task_id)
        return task

    async def list_tasks(self) -> list[ScheduledTask]:
        return await self.repo.list_tasks()

    async def update_config(self, task_id: str, **fields) -> ScheduledTask:
        task = await self._get_task_or_404(task_id)
        for key, value in fields.items():
            setattr(task, key, value)
        return await self.repo.update_task(task)

    async def preview(self, task_id: str) -> PreviewResult:
        task = await self._get_task_or_404(task_id)
        handler = self.handlers[task.task_type]
        deals = await self.deal_repo.get_active_without_expiry_with_asin()
        return await run_in_threadpool(handler.evaluate, deals, task.config)

    async def confirm(
        self, task_id: str, total_checked: int, candidates: list[Candidate], triggered_by: str
    ) -> ScheduledTaskRun:
        task = await self._get_task_or_404(task_id)
        handler = self.handlers[task.task_type]
        deleted = await handler.execute(candidates)
        run = await self._persist_run(
            task, trigger_type="manual", status="completed",
            total_checked=total_checked, deleted=deleted, triggered_by=triggered_by,
        )
        task.last_run_at = datetime.now(timezone.utc)
        await self.repo.update_task(task)
        return run

    async def run_automatic(self, task_id: str) -> ScheduledTaskRun:
        task = await self._get_task_or_404(task_id)
        handler = self.handlers[task.task_type]
        try:
            deals = await self.deal_repo.get_active_without_expiry_with_asin()
            result: PreviewResult = await run_in_threadpool(handler.evaluate, deals, task.config)
            deleted = await handler.execute(result.candidates)
            run = await self._persist_run(
                task, trigger_type="automatic", status="completed",
                total_checked=result.total_checked, deleted=deleted, triggered_by=None,
            )
            task.last_run_at = datetime.now(timezone.utc)
            await self.repo.update_task(task)
            return run
        except Exception as exc:
            logger.exception("Fallo ejecutando la tarea programada %s", task_id)
            now = datetime.now(timezone.utc)
            failed_run = ScheduledTaskRun(
                task_id=task.id, trigger_type="automatic", status="failed",
                started_at=now, finished_at=now, total_checked=0, total_affected=0,
                triggered_by=None, error_message=str(exc)[:500],
            )
            await self.repo.create_run(failed_run)
            raise

    async def _persist_run(self, task, *, trigger_type, status, total_checked, deleted, triggered_by):
        now = datetime.now(timezone.utc)
        run = ScheduledTaskRun(
            task_id=task.id, trigger_type=trigger_type, status=status,
            started_at=now, finished_at=now, total_checked=total_checked,
            total_affected=len(deleted), triggered_by=triggered_by,
        )
        run.items = [self._candidate_to_item(c) for c in deleted]
        created = await self.repo.create_run(run)
        for candidate in deleted:
            await audit_log(
                self.session,
                user_id=triggered_by,
                action="deal.auto_delete_price_check",
                target_type="deal",
                target_id=candidate.deal_id,
                payload={
                    "old_price": float(candidate.old_price),
                    "new_price": float(candidate.new_price) if candidate.new_price is not None else None,
                    "reason": candidate.reason,
                },
            )
        return created

    @staticmethod
    def _candidate_to_item(candidate: Candidate) -> ScheduledTaskRunItem:
        return ScheduledTaskRunItem(
            deal_id_snapshot=candidate.deal_id,
            title=candidate.title,
            slug=candidate.slug,
            image_url=candidate.image_url,
            description=candidate.description,
            store_id=candidate.store_id,
            store_name=candidate.store_name,
            category_id=candidate.category_id,
            subcategory_id=candidate.subcategory_id,
            external_id=candidate.external_id,
            affiliate_url=candidate.affiliate_url,
            source_url=candidate.source_url,
            old_price=candidate.old_price,
            new_price=candidate.new_price,
            reason=candidate.reason,
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd buenchollo-api && pytest app/tests/test_scheduled_task_service.py -v`
Expected: 10 passed.

- [ ] **Step 6: Commit**

```bash
git add buenchollo-api/app/modules/scheduled_tasks/domain/exceptions.py buenchollo-api/app/modules/scheduled_tasks/application/scheduled_task_service.py buenchollo-api/app/tests/test_scheduled_task_service.py
git commit -m "feat: add ScheduledTaskService (config, preview, confirm, automatic run)"
```

---

### Task 6: `ScheduledTaskService` — run history & restore

**Files:**
- Modify: `buenchollo-api/app/modules/scheduled_tasks/domain/exceptions.py` (already has `RunItemNotFound`, `ItemAlreadyRestoredError`, `RestoreFailedError` from Task 5 — no change needed here, listed for context)
- Modify: `buenchollo-api/app/modules/scheduled_tasks/application/scheduled_task_service.py`
- Test: `buenchollo-api/app/tests/test_scheduled_task_service.py`

**Interfaces:**
- Consumes: `Deal` (`app/modules/deals/domain/models.py`), `auto_slug` (`app/modules/deals/domain/utils.py`), `sqlalchemy.exc.IntegrityError`.
- Produces: `ScheduledTaskService.list_runs(task_id, limit, offset)`, `.get_run_detail(run_id)`, `.delete_run(run_id) -> bool`, `.bulk_delete_runs(run_ids) -> int`, `.restore_item(item_id) -> Deal` — consumed by Task 9 (API).

- [ ] **Step 1: Write the failing unit tests**

Append to `buenchollo-api/app/tests/test_scheduled_task_service.py`:

```python
from app.modules.scheduled_tasks.domain.exceptions import (
    ItemAlreadyRestoredError,
    RestoreFailedError,
    RunItemNotFound,
)


def _run_item(**overrides):
    base = dict(
        id="item-1",
        title="Producto X",
        slug="producto-x",
        description="desc",
        image_url="https://img/x.jpg",
        affiliate_url="https://amazon.es/dp/B0D9WH9WLD",
        source_url=None,
        external_id="B0D9WH9WLD",
        store_id="store-1",
        category_id="cat-1",
        subcategory_id=None,
        old_price=Decimal("100.00"),
        restored_at=None,
        restored_deal_id=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _build_service_for_history():
    repo = MagicMock()
    deal_repo = MagicMock()
    session = MagicMock()
    service = ScheduledTaskService(repo, deal_repo, {}, session)
    return service, repo, deal_repo


@pytest.mark.asyncio
async def test_list_runs_delega_en_el_repositorio():
    service, repo, _ = _build_service_for_history()
    repo.list_runs = AsyncMock(return_value=["run-a"])

    result = await service.list_runs("task-1", limit=10, offset=0)

    repo.list_runs.assert_awaited_once_with("task-1", limit=10, offset=0)
    assert result == ["run-a"]


@pytest.mark.asyncio
async def test_delete_run_true_si_existia():
    service, repo, _ = _build_service_for_history()
    run = SimpleNamespace(id="run-1")
    repo.get_run_by_id = AsyncMock(return_value=run)
    repo.delete_run = AsyncMock()

    deleted = await service.delete_run("run-1")

    assert deleted is True
    repo.delete_run.assert_awaited_once_with(run)


@pytest.mark.asyncio
async def test_delete_run_false_si_no_existia():
    service, repo, _ = _build_service_for_history()
    repo.get_run_by_id = AsyncMock(return_value=None)

    deleted = await service.delete_run("no-existe")

    assert deleted is False


@pytest.mark.asyncio
async def test_bulk_delete_runs_delega_en_el_repositorio():
    service, repo, _ = _build_service_for_history()
    repo.delete_runs_by_ids = AsyncMock(return_value=3)

    count = await service.bulk_delete_runs(["r1", "r2", "r3"])

    assert count == 3
    repo.delete_runs_by_ids.assert_awaited_once_with(["r1", "r2", "r3"])


@pytest.mark.asyncio
async def test_restore_item_crea_deal_activo_y_marca_restaurado():
    service, repo, deal_repo = _build_service_for_history()
    item = _run_item()
    repo.get_run_item_by_id = AsyncMock(return_value=item)
    repo.update_run_item = AsyncMock(side_effect=lambda i: i)
    created = SimpleNamespace(id="new-deal-1")
    reloaded = SimpleNamespace(id="new-deal-1", title="Producto X", store=None, category=None)
    deal_repo.create = AsyncMock(return_value=created)
    deal_repo.get_by_id = AsyncMock(return_value=reloaded)

    result = await service.restore_item("item-1")

    assert result is reloaded  # recargado con relaciones precargadas, no el objeto crudo de create()
    deal_repo.get_by_id.assert_awaited_once_with("new-deal-1")
    created_deal = deal_repo.create.call_args.args[0]
    assert created_deal.title == "Producto X"
    assert created_deal.status == "active"
    assert created_deal.current_price == Decimal("100.00")
    assert item.restored_at is not None
    assert item.restored_deal_id == "new-deal-1"
    repo.update_run_item.assert_awaited_once_with(item)


@pytest.mark.asyncio
async def test_restore_item_lanza_not_found_si_no_existe():
    service, repo, _ = _build_service_for_history()
    repo.get_run_item_by_id = AsyncMock(return_value=None)

    with pytest.raises(RunItemNotFound):
        await service.restore_item("no-existe")


@pytest.mark.asyncio
async def test_restore_item_lanza_conflict_si_ya_estaba_restaurado():
    service, repo, _ = _build_service_for_history()
    item = _run_item(restored_at=datetime(2026, 8, 1, tzinfo=timezone.utc), restored_deal_id="old-deal")
    repo.get_run_item_by_id = AsyncMock(return_value=item)

    with pytest.raises(ItemAlreadyRestoredError):
        await service.restore_item("item-1")


@pytest.mark.asyncio
async def test_restore_item_traduce_integrity_error_a_restore_failed():
    from sqlalchemy.exc import IntegrityError

    service, repo, deal_repo = _build_service_for_history()
    item = _run_item()
    repo.get_run_item_by_id = AsyncMock(return_value=item)
    deal_repo.create = AsyncMock(side_effect=IntegrityError("stmt", {}, Exception("fk violation")))

    with pytest.raises(RestoreFailedError):
        await service.restore_item("item-1")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd buenchollo-api && pytest app/tests/test_scheduled_task_service.py -v -k "list_runs or delete_run or bulk_delete or restore_item"`
Expected: FAIL — `AttributeError: 'ScheduledTaskService' object has no attribute 'list_runs'` (and similar for the rest).

- [ ] **Step 3: Implement the methods**

In `buenchollo-api/app/modules/scheduled_tasks/application/scheduled_task_service.py`, add the imports:

```python
from sqlalchemy.exc import IntegrityError

from app.modules.deals.domain.models import Deal
from app.modules.deals.domain.utils import auto_slug
from app.modules.scheduled_tasks.domain.exceptions import (
    ItemAlreadyRestoredError,
    RestoreFailedError,
    RunItemNotFound,
    ScheduledTaskNotFound,
)
```

(`ScheduledTaskNotFound` is already imported — merge into the existing import line instead of duplicating it.)

Add these methods to `ScheduledTaskService` (after `run_automatic`, before `_persist_run`):

```python
    async def list_runs(self, task_id: str, limit: int = 50, offset: int = 0) -> list[ScheduledTaskRun]:
        return await self.repo.list_runs(task_id, limit=limit, offset=offset)

    async def get_run_detail(self, run_id: str) -> ScheduledTaskRun | None:
        return await self.repo.get_run_by_id(run_id)

    async def delete_run(self, run_id: str) -> bool:
        run = await self.repo.get_run_by_id(run_id)
        if run is None:
            return False
        await self.repo.delete_run(run)
        return True

    async def bulk_delete_runs(self, run_ids: list[str]) -> int:
        return await self.repo.delete_runs_by_ids(run_ids)

    async def restore_item(self, item_id: str) -> Deal:
        item = await self.repo.get_run_item_by_id(item_id)
        if item is None:
            raise RunItemNotFound(item_id)
        if item.restored_at is not None:
            raise ItemAlreadyRestoredError(item_id)

        new_deal = Deal(
            title=item.title,
            slug=auto_slug(item.title),
            description=item.description,
            image_url=item.image_url,
            current_price=item.old_price,
            affiliate_url=item.affiliate_url,
            source_url=item.source_url,
            external_id=item.external_id,
            store_id=item.store_id,
            category_id=item.category_id,
            subcategory_id=item.subcategory_id,
            status="active",
            source="manual",
        )
        try:
            created = await self.deal_repo.create(new_deal)
        except IntegrityError as exc:
            raise RestoreFailedError(item_id) from exc

        item.restored_at = datetime.now(timezone.utc)
        item.restored_deal_id = created.id
        await self.repo.update_run_item(item)
        # Recargar con category/subcategory/store precargados (_base_deal_query):
        # el objeto recién creado no las tiene cargadas, y DealDetailResponse
        # las serializa — un lazy-load async no soportado (MissingGreenlet),
        # el mismo problema que ScheduledDealRepository.update ya tuvo que
        # resolver. Mismo patrón que DealService.create_deal.
        return await self.deal_repo.get_by_id(created.id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd buenchollo-api && pytest app/tests/test_scheduled_task_service.py -v`
Expected: all pass (18 total).

- [ ] **Step 5: Commit**

```bash
git add buenchollo-api/app/modules/scheduled_tasks/application/scheduled_task_service.py buenchollo-api/app/tests/test_scheduled_task_service.py
git commit -m "feat: add run history listing, deletion and restore to ScheduledTaskService"
```

---

### Task 7: Scheduler wiring

**Files:**
- Create: `buenchollo-api/app/modules/scheduled_tasks/application/scheduler.py`
- Modify: `buenchollo-api/app/modules/deals/application/scheduler.py`
- Modify: `buenchollo-api/app/tests/test_scheduler_builder.py`
- Test: `buenchollo-api/app/tests/test_scheduled_tasks_scheduler.py`

**Interfaces:**
- Consumes: `ScheduledTaskRepository` (Task 3), `PriceCheckHandler` (Task 4), `ScheduledTaskService`, `is_task_due` (Task 5/6), `AmazonProductClient` (`app/modules/products/infrastructure/amazon_client.py`), `DealRepository` (`app/modules/deals/infrastructure/repository.py`).
- Produces: `run_due_scheduled_tasks(settings: Settings) -> int` in `app.modules.scheduled_tasks.application.scheduler` — registered as a new APScheduler job (`id="run_scheduled_tasks"`) in `build_deals_scheduler()`.

- [ ] **Step 1: Write the failing tests for the new scheduler module**

Create `buenchollo-api/app/tests/test_scheduled_tasks_scheduler.py`:

```python
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import Settings
from app.modules.scheduled_tasks.application.scheduler import _execute_due_tasks, _run


def _task(task_id: str, *, enabled: bool = True, run_hour: int = 0, last_run_at=None, frequency_preset="weekly"):
    return SimpleNamespace(
        id=task_id, enabled=enabled, run_hour=run_hour,
        last_run_at=last_run_at, frequency_preset=frequency_preset,
    )


class FakeRepo:
    def __init__(self, tasks):
        self.tasks = tasks

    async def get_enabled_tasks(self):
        return self.tasks


@pytest.mark.asyncio
async def test_execute_due_tasks_ejecuta_solo_las_debidas():
    due = _task("task-1", run_hour=0)
    not_due = _task("task-2", enabled=False)
    repo = FakeRepo([due, not_due])
    service = MagicMock()
    service.run_automatic = AsyncMock()

    executed = await _execute_due_tasks(repo, service, datetime(2026, 8, 10, 5, tzinfo=timezone.utc))

    assert executed == 1
    service.run_automatic.assert_awaited_once_with("task-1")


@pytest.mark.asyncio
async def test_execute_due_tasks_continua_si_una_tarea_falla():
    task_a = _task("task-1", run_hour=0)
    task_b = _task("task-2", run_hour=0)
    repo = FakeRepo([task_a, task_b])
    service = MagicMock()
    service.run_automatic = AsyncMock(side_effect=[RuntimeError("boom"), None])

    executed = await _execute_due_tasks(repo, service, datetime(2026, 8, 10, 5, tzinfo=timezone.utc))

    assert executed == 1  # task-1 falló (no cuenta), task-2 se ejecuta igualmente
    assert service.run_automatic.await_count == 2


@pytest.mark.asyncio
async def test_run_devuelve_cero_sin_database_url():
    settings = Settings(database_url="")

    executed = await _run(settings)

    assert executed == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd buenchollo-api && pytest app/tests/test_scheduled_tasks_scheduler.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write the scheduler module**

Create `buenchollo-api/app/modules/scheduled_tasks/application/scheduler.py`:

```python
"""Job de mantenimiento de la tarea programada de revisión de precios.

Mismo patrón que `scheduled_deals/application/publication_worker.py`:
engine dedicado con NullPool (proceso de fondo, no el pool del web),
envuelto en `asyncio.run()` porque APScheduler (BackgroundScheduler) sólo
llama funciones síncronas. El bucle de "qué tareas tocan" vive en
`_execute_due_tasks`, separado de la creación del engine/sesión, para
poder testearlo con fakes en vez de mockear SQLAlchemy (mismo motivo por
el que `ScheduledPublicationWorker.process_due` es una clase aparte).
"""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.modules.deals.infrastructure.repository import DealRepository
from app.modules.products.infrastructure.amazon_client import AmazonProductClient
from app.modules.scheduled_tasks.application.price_check_handler import PriceCheckHandler
from app.modules.scheduled_tasks.application.scheduled_task_service import (
    ScheduledTaskService,
    is_task_due,
)
from app.modules.scheduled_tasks.infrastructure.repository import ScheduledTaskRepository

logger = logging.getLogger(__name__)


async def _execute_due_tasks(repo, service, now_local: datetime) -> int:
    executed = 0
    tasks = await repo.get_enabled_tasks()
    for task in tasks:
        if not is_task_due(task, now_local):
            continue
        try:
            await service.run_automatic(task.id)
            executed += 1
        except Exception:
            logger.exception("Fallo al ejecutar la tarea programada %s", task.id)
    return executed


async def _run(settings: Settings) -> int:
    if not settings.database_url:
        logger.error("DATABASE_URL no configurada para el worker de tareas programadas")
        return 0

    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
        connect_args={"server_settings": {"jit": "off"}, "statement_cache_size": 0},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            try:
                repo = ScheduledTaskRepository(session)
                deal_repo = DealRepository(session)
                handler = PriceCheckHandler(AmazonProductClient(settings), deal_repo)
                service = ScheduledTaskService(repo, deal_repo, {"price_check": handler}, session)

                now_local = datetime.now(timezone.utc).astimezone()
                executed = await _execute_due_tasks(repo, service, now_local)
                await session.commit()
                return executed
            except Exception:
                await session.rollback()
                logger.exception("Fallo global del worker de tareas programadas")
                return 0
    finally:
        await engine.dispose()


def run_due_scheduled_tasks(settings: Settings) -> int:
    return asyncio.run(_run(settings))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd buenchollo-api && pytest app/tests/test_scheduled_tasks_scheduler.py -v`
Expected: 3 passed.

- [ ] **Step 5: Register the job in `build_deals_scheduler`**

In `buenchollo-api/app/modules/deals/application/scheduler.py`, add the import (after line 14):

```python
from app.modules.scheduled_tasks.application.scheduler import run_due_scheduled_tasks
```

Add the job registration inside `build_deals_scheduler`, right before the `return scheduler, cleaner` line:

```python
    scheduler.add_job(
        run_due_scheduled_tasks,
        "interval",
        hours=1,
        args=[settings],
        id="run_scheduled_tasks",
        max_instances=1,
        coalesce=True,
    )
```

Update the module docstring reference comment at the end of `main.py`'s lifespan log message and `run_scheduler.py`'s log message is NOT required (they're informational strings, not test-asserted) — skip.

- [ ] **Step 6: Update the existing job-count test**

In `buenchollo-api/app/tests/test_scheduler_builder.py`, replace:

```python
def test_builder_registra_los_cuatro_jobs_sin_arrancar():
    scheduler, cleaner = build_deals_scheduler(Settings())
    jobs = scheduler.get_jobs()
    assert len(jobs) == 4
    names = {job.func.__name__ for job in jobs}
    assert names == {
        "mark_expired_deals",
        "run_due_scheduled_publications",
        "clean_expired_deals",
        "run_due_scheduled_posts",
    }
    assert scheduler.running is False
    assert cleaner is not None
```

with:

```python
def test_builder_registra_los_cinco_jobs_sin_arrancar():
    scheduler, cleaner = build_deals_scheduler(Settings())
    jobs = scheduler.get_jobs()
    assert len(jobs) == 5
    names = {job.func.__name__ for job in jobs}
    assert names == {
        "mark_expired_deals",
        "run_due_scheduled_publications",
        "clean_expired_deals",
        "run_due_scheduled_posts",
        "run_due_scheduled_tasks",
    }
    assert scheduler.running is False
    assert cleaner is not None
```

- [ ] **Step 7: Run both scheduler tests to verify they pass**

Run: `cd buenchollo-api && pytest app/tests/test_scheduler_builder.py app/tests/test_scheduled_tasks_scheduler.py -v`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add buenchollo-api/app/modules/scheduled_tasks/application/scheduler.py buenchollo-api/app/modules/deals/application/scheduler.py buenchollo-api/app/tests/test_scheduler_builder.py buenchollo-api/app/tests/test_scheduled_tasks_scheduler.py
git commit -m "feat: register the hourly scheduled-tasks job in the deals scheduler"
```

---

### Task 8: API — config, preview, confirm endpoints

**Files:**
- Create: `buenchollo-api/app/modules/scheduled_tasks/api/__init__.py`
- Create: `buenchollo-api/app/modules/scheduled_tasks/api/schemas.py`
- Create: `buenchollo-api/app/modules/scheduled_tasks/api/router.py`
- Modify: `buenchollo-api/app/main.py`
- Test: `buenchollo-api/app/tests/test_scheduled_tasks_api.py`

**Interfaces:**
- Consumes: `ScheduledTaskService` (Task 5/6), `ScheduledTaskRepository` (Task 3), `PriceCheckHandler` (Task 4), `require_admin`/`get_current_user` (`app/core/security.py`), `audit_log` (`app/core/audit/service.py`), `get_db` (`app/core/database.py`), `get_settings` (`app/core/config.py`).
- Produces: `router` (prefix `/admin/scheduled-tasks`) with `GET ""`, `PUT "/{task_id}"`, `POST "/{task_id}/preview"`, `POST "/{task_id}/confirm"` — mounted at `/v1` in `main.py`. `get_scheduled_task_service` dependency — reused by Task 9.

- [ ] **Step 1: Write the failing integration tests**

Create `buenchollo-api/app/modules/scheduled_tasks/api/__init__.py` (empty file).

Create `buenchollo-api/app/tests/test_scheduled_tasks_api.py`:

```python
"""Tests de integración del panel de tareas programadas. Requieren
PostgreSQL real (excluidos del CI con -m "not integration")."""
from unittest.mock import patch

import pytest

from app.core.security import require_admin
from app.main import app

pytestmark = pytest.mark.integration


class MockUser:
    id = "dbe6e006-4f3e-4be8-8351-7e264ed3acb6"


async def mock_require_admin():
    return MockUser()


@pytest.fixture(autouse=True)
def override_admin():
    app.dependency_overrides[require_admin] = mock_require_admin
    yield
    app.dependency_overrides.clear()


def _get_price_check_task_id(client) -> str:
    response = client.get("/v1/admin/scheduled-tasks")
    assert response.status_code == 200, response.text
    tasks = response.json()
    price_check = next(t for t in tasks if t["task_type"] == "price_check")
    return price_check["id"]


def test_list_scheduled_tasks_incluye_price_check_seed(integration_client):
    task_id = _get_price_check_task_id(integration_client)
    assert task_id


def test_update_scheduled_task_cambia_config(integration_client):
    task_id = _get_price_check_task_id(integration_client)

    response = integration_client.put(
        f"/v1/admin/scheduled-tasks/{task_id}",
        json={"enabled": True, "frequency_preset": "daily", "run_hour": 6, "config": {"price_tolerance_percent": 15}},
    )

    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["enabled"] is True
    assert updated["frequency_preset"] == "daily"
    assert updated["run_hour"] == 6
    assert updated["config"]["price_tolerance_percent"] == 15


def test_preview_sin_candidatos_devuelve_lista_vacia(integration_client):
    task_id = _get_price_check_task_id(integration_client)

    with patch(
        "app.modules.scheduled_tasks.api.router.AmazonProductClient"
    ) as mock_client_cls:
        mock_client_cls.return_value.get_product_preview.return_value = None
        response = integration_client.post(f"/v1/admin/scheduled-tasks/{task_id}/preview")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["candidates"] == []


def test_confirm_borra_el_deal_y_crea_el_registro(integration_client):
    task_id = _get_price_check_task_id(integration_client)

    create_resp = integration_client.post(
        "/v1/deals/admin",
        json={
            "title": "Auriculares Test Price Check",
            "current_price": 50.0,
            "affiliate_url": "https://amazon.es/dp/B0TESTPRICE",
            "external_id": "B0TESTPRICE",
            "status": "active",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    deal = create_resp.json()

    confirm_payload = {
        "total_checked": 1,
        "candidates": [
            {
                "deal_id": deal["id"],
                "title": deal["title"],
                "slug": deal["slug"],
                "image_url": None,
                "description": None,
                "store_id": None,
                "store_name": None,
                "category_id": None,
                "subcategory_id": None,
                "external_id": "B0TESTPRICE",
                "affiliate_url": deal["affiliate_url"],
                "source_url": None,
                "old_price": 50.0,
                "new_price": 65.0,
                "reason": "price_increase",
            }
        ],
    }
    response = integration_client.post(
        f"/v1/admin/scheduled-tasks/{task_id}/confirm", json=confirm_payload
    )

    assert response.status_code == 200, response.text
    run = response.json()
    assert run["trigger_type"] == "manual"
    assert run["total_affected"] == 1

    get_deal_resp = integration_client.get(f"/v1/deals/{deal['slug']}")
    assert get_deal_resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd buenchollo-api && pytest app/tests/test_scheduled_tasks_api.py -v -m integration`
Expected: FAIL — `ModuleNotFoundError` / 404s (router doesn't exist yet).

- [ ] **Step 3: Write the schemas**

Create `buenchollo-api/app/modules/scheduled_tasks/api/schemas.py`:

```python
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_FrequencyPreset = Literal["daily", "weekly", "biweekly", "monthly"]
_Reason = Literal["price_increase", "no_longer_deal", "out_of_stock"]


class ScheduledTaskResponse(BaseModel):
    id: str
    task_type: str
    enabled: bool
    frequency_preset: str
    run_hour: int
    config: dict
    last_run_at: datetime | None
    model_config = ConfigDict(from_attributes=True)


class ScheduledTaskUpdate(BaseModel):
    enabled: bool | None = None
    frequency_preset: _FrequencyPreset | None = None
    run_hour: int | None = Field(default=None, ge=0, le=23)
    config: dict | None = None


class CandidateSchema(BaseModel):
    deal_id: str
    title: str
    slug: str
    image_url: str | None = None
    description: str | None = None
    store_id: str | None = None
    store_name: str | None = None
    category_id: str | None = None
    subcategory_id: str | None = None
    external_id: str
    affiliate_url: str
    source_url: str | None = None
    old_price: Decimal
    new_price: Decimal | None = None
    reason: _Reason


class PreviewResponse(BaseModel):
    total_checked: int
    candidates: list[CandidateSchema]


class ConfirmRequest(BaseModel):
    total_checked: int
    candidates: list[CandidateSchema]


class RunResponse(BaseModel):
    id: str
    trigger_type: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    total_checked: int
    total_affected: int
    triggered_by: str | None
    error_message: str | None
    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 4: Write the router**

Create `buenchollo-api/app/modules/scheduled_tasks/api/router.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_log
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import require_admin
from app.modules.deals.infrastructure.repository import DealRepository
from app.modules.products.infrastructure.amazon_client import AmazonProductClient
from app.modules.scheduled_tasks.api.schemas import (
    CandidateSchema,
    ConfirmRequest,
    PreviewResponse,
    RunResponse,
    ScheduledTaskResponse,
    ScheduledTaskUpdate,
)
from app.modules.scheduled_tasks.application.price_check_handler import PriceCheckHandler
from app.modules.scheduled_tasks.application.scheduled_task_service import ScheduledTaskService
from app.modules.scheduled_tasks.application.task_handler import Candidate
from app.modules.scheduled_tasks.infrastructure.repository import ScheduledTaskRepository

router = APIRouter(prefix="/admin/scheduled-tasks", tags=["scheduled-tasks"])


def get_scheduled_task_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ScheduledTaskService:
    repo = ScheduledTaskRepository(db)
    deal_repo = DealRepository(db)
    handler = PriceCheckHandler(AmazonProductClient(settings), deal_repo)
    return ScheduledTaskService(repo, deal_repo, {"price_check": handler}, db)


@router.get("", response_model=list[ScheduledTaskResponse])
async def list_scheduled_tasks(
    service: ScheduledTaskService = Depends(get_scheduled_task_service),
    _auth=Depends(require_admin),
):
    return await service.list_tasks()


@router.put("/{task_id}", response_model=ScheduledTaskResponse)
async def update_scheduled_task(
    task_id: str,
    payload: ScheduledTaskUpdate,
    db: AsyncSession = Depends(get_db),
    service: ScheduledTaskService = Depends(get_scheduled_task_service),
    current_user=Depends(require_admin),
):
    changes = payload.model_dump(exclude_none=True)
    updated = await service.update_config(task_id, **changes)
    await audit_log(
        db,
        user_id=str(current_user.id),
        action="scheduled_task.update",
        target_type="scheduled_task",
        target_id=task_id,
        payload={"changed_fields": list(changes)},
    )
    return updated


@router.post("/{task_id}/preview", response_model=PreviewResponse)
async def preview_scheduled_task(
    task_id: str,
    service: ScheduledTaskService = Depends(get_scheduled_task_service),
    _auth=Depends(require_admin),
):
    result = await service.preview(task_id)
    return PreviewResponse(
        total_checked=result.total_checked,
        candidates=[CandidateSchema.model_validate(c.__dict__) for c in result.candidates],
    )


@router.post("/{task_id}/confirm", response_model=RunResponse)
async def confirm_scheduled_task(
    task_id: str,
    payload: ConfirmRequest,
    db: AsyncSession = Depends(get_db),
    service: ScheduledTaskService = Depends(get_scheduled_task_service),
    current_user=Depends(require_admin),
):
    candidates = [Candidate(**c.model_dump()) for c in payload.candidates]
    return await service.confirm(task_id, payload.total_checked, candidates, str(current_user.id))
```

- [ ] **Step 5: Register the router in `main.py`**

In `buenchollo-api/app/main.py`, add the import after line 32 (`from app.modules.scheduled_deals.api.router import router as scheduled_deals_router`):

```python
from app.modules.scheduled_tasks.api.router import router as scheduled_tasks_router
```

Add to the `v1.include_router(...)` block, after `v1.include_router(scheduled_deals_router)`:

```python
v1.include_router(scheduled_tasks_router)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd buenchollo-api && pytest app/tests/test_scheduled_tasks_api.py -v -m integration`
Expected: 4 passed. (Requires a real Postgres reachable via the `.env` used by `conftest.py` — same requirement as `test_deals_api.py`.)

- [ ] **Step 7: Commit**

```bash
git add buenchollo-api/app/modules/scheduled_tasks/api/ buenchollo-api/app/main.py buenchollo-api/app/tests/test_scheduled_tasks_api.py
git commit -m "feat: add scheduled-tasks config/preview/confirm API endpoints"
```

---

### Task 9: API — run history & restore endpoints

**Files:**
- Modify: `buenchollo-api/app/modules/scheduled_tasks/api/schemas.py`
- Modify: `buenchollo-api/app/modules/scheduled_tasks/api/router.py`
- Modify: `buenchollo-api/app/tests/test_scheduled_tasks_api.py`

**Interfaces:**
- Consumes: `ScheduledTaskService.list_runs/get_run_detail/delete_run/bulk_delete_runs/restore_item` (Task 6), `ScheduledTaskRunNotFound`/`RunItemNotFound` (Task 5/6), `DealDetailResponse` (`app/modules/deals/api/schemas.py`).
- Produces: `GET /admin/scheduled-tasks/{task_id}/runs`, `GET /admin/scheduled-tasks/runs/{run_id}`, `DELETE /admin/scheduled-tasks/runs/{run_id}`, `POST /admin/scheduled-tasks/runs/bulk-delete`, `POST /admin/scheduled-tasks/runs/items/{item_id}/restore`.

- [ ] **Step 1: Write the failing integration tests**

Append to `buenchollo-api/app/tests/test_scheduled_tasks_api.py`:

```python
def _create_deal(client, *, asin: str, price: float = 50.0) -> dict:
    resp = client.post(
        "/v1/deals/admin",
        json={
            "title": f"Producto {asin}",
            "current_price": price,
            "affiliate_url": f"https://amazon.es/dp/{asin}",
            "external_id": asin,
            "status": "active",
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _confirm_deletion(client, task_id: str, deal: dict, *, reason: str = "price_increase") -> dict:
    payload = {
        "total_checked": 1,
        "candidates": [
            {
                "deal_id": deal["id"],
                "title": deal["title"],
                "slug": deal["slug"],
                "image_url": None,
                "description": None,
                "store_id": None,
                "store_name": None,
                "category_id": None,
                "subcategory_id": None,
                "external_id": deal["external_id"],
                "affiliate_url": deal["affiliate_url"],
                "source_url": None,
                "old_price": deal["current_price"],
                "new_price": deal["current_price"] + 20,
                "reason": reason,
            }
        ],
    }
    resp = client.post(f"/v1/admin/scheduled-tasks/{task_id}/confirm", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_list_runs_devuelve_el_run_recien_creado(integration_client):
    task_id = _get_price_check_task_id(integration_client)
    deal = _create_deal(integration_client, asin="B0RUNLIST01")
    run = _confirm_deletion(integration_client, task_id, deal)

    resp = integration_client.get(f"/v1/admin/scheduled-tasks/{task_id}/runs")

    assert resp.status_code == 200, resp.text
    run_ids = [r["id"] for r in resp.json()]
    assert run["id"] in run_ids


def test_get_run_detail_incluye_los_items(integration_client):
    task_id = _get_price_check_task_id(integration_client)
    deal = _create_deal(integration_client, asin="B0RUNDETAIL1")
    run = _confirm_deletion(integration_client, task_id, deal)

    resp = integration_client.get(f"/v1/admin/scheduled-tasks/runs/{run['id']}")

    assert resp.status_code == 200, resp.text
    detail = resp.json()
    assert len(detail["items"]) == 1
    assert detail["items"][0]["deal_id_snapshot"] == deal["id"]
    assert detail["items"][0]["restored_at"] is None


def test_restore_item_recrea_el_deal_activo(integration_client):
    task_id = _get_price_check_task_id(integration_client)
    deal = _create_deal(integration_client, asin="B0RESTORE001")
    run = _confirm_deletion(integration_client, task_id, deal)
    detail = integration_client.get(f"/v1/admin/scheduled-tasks/runs/{run['id']}").json()
    item_id = detail["items"][0]["id"]

    resp = integration_client.post(f"/v1/admin/scheduled-tasks/runs/items/{item_id}/restore")

    assert resp.status_code == 200, resp.text
    restored = resp.json()
    assert restored["status"] == "active"
    assert restored["external_id"] == "B0RESTORE001"

    detail_after = integration_client.get(f"/v1/admin/scheduled-tasks/runs/{run['id']}").json()
    assert detail_after["items"][0]["restored_at"] is not None


def test_restore_item_ya_restaurado_devuelve_409(integration_client):
    task_id = _get_price_check_task_id(integration_client)
    deal = _create_deal(integration_client, asin="B0RESTORE002")
    run = _confirm_deletion(integration_client, task_id, deal)
    detail = integration_client.get(f"/v1/admin/scheduled-tasks/runs/{run['id']}").json()
    item_id = detail["items"][0]["id"]
    integration_client.post(f"/v1/admin/scheduled-tasks/runs/items/{item_id}/restore")

    resp = integration_client.post(f"/v1/admin/scheduled-tasks/runs/items/{item_id}/restore")

    assert resp.status_code == 409


def test_delete_run_lo_elimina(integration_client):
    task_id = _get_price_check_task_id(integration_client)
    deal = _create_deal(integration_client, asin="B0DELETERUN1")
    run = _confirm_deletion(integration_client, task_id, deal)

    resp = integration_client.delete(f"/v1/admin/scheduled-tasks/runs/{run['id']}")
    assert resp.status_code == 204

    detail_resp = integration_client.get(f"/v1/admin/scheduled-tasks/runs/{run['id']}")
    assert detail_resp.status_code == 404


def test_bulk_delete_runs_borra_varios(integration_client):
    task_id = _get_price_check_task_id(integration_client)
    deal_a = _create_deal(integration_client, asin="B0BULK000001")
    deal_b = _create_deal(integration_client, asin="B0BULK000002")
    run_a = _confirm_deletion(integration_client, task_id, deal_a)
    run_b = _confirm_deletion(integration_client, task_id, deal_b)

    resp = integration_client.post(
        "/v1/admin/scheduled-tasks/runs/bulk-delete",
        json={"run_ids": [run_a["id"], run_b["id"]]},
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["deleted"] == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd buenchollo-api && pytest app/tests/test_scheduled_tasks_api.py -v -m integration -k "run or restore or bulk_delete"`
Expected: FAIL — 404s (endpoints don't exist yet).

- [ ] **Step 3: Add the remaining schemas**

In `buenchollo-api/app/modules/scheduled_tasks/api/schemas.py`, add after `RunResponse`:

```python
class RunItemResponse(BaseModel):
    id: str
    deal_id_snapshot: str
    title: str
    slug: str
    image_url: str | None
    store_name: str | None
    old_price: Decimal
    new_price: Decimal | None
    reason: str
    restored_at: datetime | None
    restored_deal_id: str | None
    model_config = ConfigDict(from_attributes=True)


class RunDetailResponse(RunResponse):
    items: list[RunItemResponse]


class BulkDeleteRunsRequest(BaseModel):
    run_ids: list[str]


class BulkDeleteRunsResponse(BaseModel):
    deleted: int
```

- [ ] **Step 4: Add the endpoints**

In `buenchollo-api/app/modules/scheduled_tasks/api/router.py`, update the schema import line to also bring in the new schemas:

```python
from app.modules.scheduled_tasks.api.schemas import (
    BulkDeleteRunsRequest,
    BulkDeleteRunsResponse,
    CandidateSchema,
    ConfirmRequest,
    PreviewResponse,
    RunDetailResponse,
    RunResponse,
    ScheduledTaskResponse,
    ScheduledTaskUpdate,
)
```

Add the import for the deal schema and the domain exception, and `fastapi.Query`:

```python
from fastapi import APIRouter, Depends, Query
from app.modules.deals.api.schemas import DealDetailResponse
from app.modules.scheduled_tasks.domain.exceptions import ScheduledTaskRunNotFound
```

(merge `Query` into the existing `from fastapi import APIRouter, Depends` line.)

Append the endpoints at the end of the file:

```python
@router.get("/{task_id}/runs", response_model=list[RunResponse])
async def list_scheduled_task_runs(
    task_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: ScheduledTaskService = Depends(get_scheduled_task_service),
    _auth=Depends(require_admin),
):
    return await service.list_runs(task_id, limit=limit, offset=offset)


@router.get("/runs/{run_id}", response_model=RunDetailResponse)
async def get_scheduled_task_run_detail(
    run_id: str,
    service: ScheduledTaskService = Depends(get_scheduled_task_service),
    _auth=Depends(require_admin),
):
    run = await service.get_run_detail(run_id)
    if run is None:
        raise ScheduledTaskRunNotFound(run_id)
    return run


@router.delete("/runs/{run_id}", status_code=204)
async def delete_scheduled_task_run(
    run_id: str,
    service: ScheduledTaskService = Depends(get_scheduled_task_service),
    _auth=Depends(require_admin),
):
    deleted = await service.delete_run(run_id)
    if not deleted:
        raise ScheduledTaskRunNotFound(run_id)


@router.post("/runs/bulk-delete", response_model=BulkDeleteRunsResponse)
async def bulk_delete_scheduled_task_runs(
    payload: BulkDeleteRunsRequest,
    service: ScheduledTaskService = Depends(get_scheduled_task_service),
    _auth=Depends(require_admin),
):
    count = await service.bulk_delete_runs(payload.run_ids)
    return BulkDeleteRunsResponse(deleted=count)


@router.post("/runs/items/{item_id}/restore", response_model=DealDetailResponse)
async def restore_scheduled_task_run_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    service: ScheduledTaskService = Depends(get_scheduled_task_service),
    current_user=Depends(require_admin),
):
    deal = await service.restore_item(item_id)
    await audit_log(
        db,
        user_id=str(current_user.id),
        action="deal.restore_from_price_check",
        target_type="deal",
        target_id=deal.id,
    )
    return deal
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd buenchollo-api && pytest app/tests/test_scheduled_tasks_api.py -v -m integration`
Expected: all pass (10 total).

- [ ] **Step 6: Run the full backend test suite**

Run: `cd buenchollo-api && pytest -m "not integration" -q` then `pytest -m integration -q`
Expected: all green, no regressions in the other 30+ existing test files (in particular `test_scheduler_builder.py` and `test_deals_api.py`).

- [ ] **Step 7: Commit**

```bash
git add buenchollo-api/app/modules/scheduled_tasks/api/schemas.py buenchollo-api/app/modules/scheduled_tasks/api/router.py buenchollo-api/app/tests/test_scheduled_tasks_api.py
git commit -m "feat: add scheduled-tasks run history, bulk-delete and restore API endpoints"
```

---

## Frontend

### Task 10: Types + API service

**Files:**
- Create: `buenchollo-web/src/services/api/scheduled-tasks.ts`

**Interfaces:**
- Consumes: `apiClient` (`src/services/api/client.ts`).
- Produces: `ScheduledTaskConfig`, `ScheduledTaskUpdatePayload`, `ScheduledTaskCandidate`, `ScheduledTaskPreview`, `ScheduledTaskRun`, `ScheduledTaskRunItem`, `ScheduledTaskRunDetail` types, and `scheduledTasksService` — consumed by Task 11 (hooks).

- [ ] **Step 1: Write the service file**

Create `buenchollo-web/src/services/api/scheduled-tasks.ts`:

```typescript
import { apiClient } from "./client";

export type FrequencyPreset = "daily" | "weekly" | "biweekly" | "monthly";
export type PriceCheckReason = "price_increase" | "no_longer_deal" | "out_of_stock";

export interface ScheduledTaskConfig {
  id: string;
  task_type: string;
  enabled: boolean;
  frequency_preset: FrequencyPreset;
  run_hour: number;
  config: { price_tolerance_percent?: number; [key: string]: unknown };
  last_run_at: string | null;
}

export interface ScheduledTaskUpdatePayload {
  enabled?: boolean;
  frequency_preset?: FrequencyPreset;
  run_hour?: number;
  config?: Record<string, unknown>;
}

export interface ScheduledTaskCandidate {
  deal_id: string;
  title: string;
  slug: string;
  image_url: string | null;
  description: string | null;
  store_id: string | null;
  store_name: string | null;
  category_id: string | null;
  subcategory_id: string | null;
  external_id: string;
  affiliate_url: string;
  source_url: string | null;
  old_price: number;
  new_price: number | null;
  reason: PriceCheckReason;
}

export interface ScheduledTaskPreview {
  total_checked: number;
  candidates: ScheduledTaskCandidate[];
}

export interface ScheduledTaskRun {
  id: string;
  trigger_type: "manual" | "automatic";
  status: "completed" | "failed";
  started_at: string;
  finished_at: string | null;
  total_checked: number;
  total_affected: number;
  triggered_by: string | null;
  error_message: string | null;
}

export interface ScheduledTaskRunItem {
  id: string;
  deal_id_snapshot: string;
  title: string;
  slug: string;
  image_url: string | null;
  store_name: string | null;
  old_price: number;
  new_price: number | null;
  reason: PriceCheckReason;
  restored_at: string | null;
  restored_deal_id: string | null;
}

export interface ScheduledTaskRunDetail extends ScheduledTaskRun {
  items: ScheduledTaskRunItem[];
}

export interface RestoredDeal {
  id: string;
  title: string;
  slug: string;
}

export const scheduledTasksService = {
  list: (): Promise<ScheduledTaskConfig[]> => apiClient.get("/admin/scheduled-tasks"),

  update: (id: string, data: ScheduledTaskUpdatePayload): Promise<ScheduledTaskConfig> =>
    apiClient.put(`/admin/scheduled-tasks/${id}`, data),

  preview: (id: string): Promise<ScheduledTaskPreview> =>
    apiClient.post(`/admin/scheduled-tasks/${id}/preview`, {}),

  confirm: (id: string, payload: ScheduledTaskPreview): Promise<ScheduledTaskRun> =>
    apiClient.post(`/admin/scheduled-tasks/${id}/confirm`, payload),

  listRuns: (id: string): Promise<ScheduledTaskRun[]> =>
    apiClient.get(`/admin/scheduled-tasks/${id}/runs`),

  getRunDetail: (runId: string): Promise<ScheduledTaskRunDetail> =>
    apiClient.get(`/admin/scheduled-tasks/runs/${runId}`),

  deleteRun: (runId: string): Promise<void> =>
    apiClient.delete(`/admin/scheduled-tasks/runs/${runId}`),

  bulkDeleteRuns: (runIds: string[]): Promise<{ deleted: number }> =>
    apiClient.post(`/admin/scheduled-tasks/runs/bulk-delete`, { run_ids: runIds }),

  restoreItem: (itemId: string): Promise<RestoredDeal> =>
    apiClient.post(`/admin/scheduled-tasks/runs/items/${itemId}/restore`, {}),
};
```

- [ ] **Step 2: Typecheck**

Run: `cd buenchollo-web && npx tsc --noEmit`
Expected: no new errors attributable to `scheduled-tasks.ts`.

- [ ] **Step 3: Commit**

```bash
git add buenchollo-web/src/services/api/scheduled-tasks.ts
git commit -m "feat: add scheduled-tasks API service and types"
```

---

### Task 11: React-query hooks

**Files:**
- Create: `buenchollo-web/src/features/admin/hooks/useScheduledTasks.ts`

**Interfaces:**
- Consumes: `scheduledTasksService` and its types (Task 10), `errorMessage` (`src/lib/errors.ts`), `toast` (`sonner`), `useQuery`/`useMutation`/`useQueryClient` (`@tanstack/react-query`).
- Produces: `useScheduledTasksConfig`, `useUpdateScheduledTask`, `usePreviewScheduledTask`, `useConfirmScheduledTask`, `useScheduledTaskRuns`, `useScheduledTaskRunDetail`, `useDeleteScheduledTaskRun`, `useBulkDeleteScheduledTaskRuns`, `useRestoreScheduledTaskItem` — consumed by Task 12/13.

- [ ] **Step 1: Write the hooks file**

Create `buenchollo-web/src/features/admin/hooks/useScheduledTasks.ts`:

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  scheduledTasksService,
  type ScheduledTaskPreview,
  type ScheduledTaskUpdatePayload,
} from "@/services/api/scheduled-tasks";
import { errorMessage } from "@/lib/errors";

const KEYS = {
  config: ["scheduled-tasks", "config"] as const,
  runs: (taskId: string) => ["scheduled-tasks", taskId, "runs"] as const,
  runDetail: (runId: string) => ["scheduled-tasks", "run", runId] as const,
};

export function useScheduledTasksConfig() {
  return useQuery({ queryKey: KEYS.config, queryFn: scheduledTasksService.list });
}

export function useUpdateScheduledTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ScheduledTaskUpdatePayload }) =>
      scheduledTasksService.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.config }),
    onError: (e) => toast.error(errorMessage(e)),
  });
}

export function usePreviewScheduledTask() {
  return useMutation({
    mutationFn: (id: string) => scheduledTasksService.preview(id),
    onError: (e) => toast.error(errorMessage(e)),
  });
}

export function useConfirmScheduledTask(taskId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ScheduledTaskPreview) => scheduledTasksService.confirm(taskId, payload),
    onSuccess: (run) => {
      qc.invalidateQueries({ queryKey: KEYS.config });
      qc.invalidateQueries({ queryKey: KEYS.runs(taskId) });
      toast.success(`Revisión ejecutada: ${run.total_affected} chollo(s) eliminado(s)`);
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
}

export function useScheduledTaskRuns(taskId: string) {
  return useQuery({
    queryKey: KEYS.runs(taskId),
    queryFn: () => scheduledTasksService.listRuns(taskId),
    enabled: !!taskId,
  });
}

export function useScheduledTaskRunDetail(runId: string | null) {
  return useQuery({
    queryKey: KEYS.runDetail(runId ?? ""),
    queryFn: () => scheduledTasksService.getRunDetail(runId as string),
    enabled: !!runId,
  });
}

export function useDeleteScheduledTaskRun(taskId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => scheduledTasksService.deleteRun(runId),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.runs(taskId) }),
    onError: (e) => toast.error(errorMessage(e)),
  });
}

export function useBulkDeleteScheduledTaskRuns(taskId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runIds: string[]) => scheduledTasksService.bulkDeleteRuns(runIds),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.runs(taskId) }),
    onError: (e) => toast.error(errorMessage(e)),
  });
}

export function useRestoreScheduledTaskItem(runId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (itemId: string) => scheduledTasksService.restoreItem(itemId),
    onSuccess: (deal) => {
      qc.invalidateQueries({ queryKey: KEYS.runDetail(runId) });
      toast.success(`Chollo restaurado: ${deal.title}`);
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
}
```

- [ ] **Step 2: Typecheck**

Run: `cd buenchollo-web && npx tsc --noEmit`
Expected: no new errors.

- [ ] **Step 3: Commit**

```bash
git add buenchollo-web/src/features/admin/hooks/useScheduledTasks.ts
git commit -m "feat: add react-query hooks for scheduled tasks"
```

---

### Task 12: Route, nav entry, and config panel (with run-now preview/confirm)

**Files:**
- Modify: `buenchollo-web/src/routes/admin.tsx`
- Create: `buenchollo-web/src/features/admin/components/ScheduledTaskConfigPanel.tsx`
- Create: `buenchollo-web/src/routes/admin.tareas-programadas.tsx`

**Interfaces:**
- Consumes: hooks from Task 11, `ScheduledTaskConfig`/`ScheduledTaskCandidate`/`ScheduledTaskPreview` types (Task 10), `AlertDialog*` (`src/components/ui/alert-dialog.tsx`), `formatPrice` (`src/lib/format.ts`).
- Produces: `ScheduledTaskConfigPanel` component (`{ task: ScheduledTaskConfig }` prop) — used by the new route. New nav link `/admin/tareas-programadas`.

- [ ] **Step 1: Add the nav entry**

In `buenchollo-web/src/routes/admin.tsx`, add `Clock` to the `lucide-react` import (line 5):

```typescript
import { Package, FolderTree, Users, BarChart3, ShoppingBag, FileText, Clock } from "lucide-react";
```

Add a new `<Link>` after the "Blog" entry (after line 71's closing `</Link>`, before "Usuarios"):

```tsx
            <Link
              to="/admin/tareas-programadas"
              activeProps={{ className: "bg-surface-700 text-cyan-glow" }}
              className="flex items-center gap-2 px-3 py-2 font-mono text-xs uppercase hover:bg-surface-700"
            >
              <Clock className="size-4" /> Tareas programadas
            </Link>
```

- [ ] **Step 2: Write the config panel component**

Create `buenchollo-web/src/features/admin/components/ScheduledTaskConfigPanel.tsx`:

```tsx
/** Configuración + ejecución manual (con confirmación) de una tarea programada. */
import { useState } from "react";
import { Play } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { formatPrice } from "@/lib/format";
import type {
  ScheduledTaskCandidate,
  ScheduledTaskConfig,
  ScheduledTaskPreview,
} from "@/services/api/scheduled-tasks";
import {
  useConfirmScheduledTask,
  usePreviewScheduledTask,
  useUpdateScheduledTask,
} from "@/features/admin/hooks/useScheduledTasks";

const REASON_LABEL: Record<ScheduledTaskCandidate["reason"], string> = {
  price_increase: "Subió de precio",
  no_longer_deal: "Ya no es oferta",
  out_of_stock: "Sin stock",
};

const FREQUENCY_LABEL: Record<ScheduledTaskConfig["frequency_preset"], string> = {
  daily: "Diario",
  weekly: "Semanal",
  biweekly: "Cada 2 semanas",
  monthly: "Mensual",
};

export function ScheduledTaskConfigPanel({ task }: { readonly task: ScheduledTaskConfig }) {
  const [pendingPreview, setPendingPreview] = useState<ScheduledTaskPreview | null>(null);
  const update = useUpdateScheduledTask();
  const preview = usePreviewScheduledTask();
  const confirm = useConfirmScheduledTask(task.id);

  const tolerance = task.config.price_tolerance_percent ?? 10;

  const handleRunNow = async () => {
    const result = await preview.mutateAsync(task.id);
    if (result.candidates.length === 0) {
      setPendingPreview(null);
      return;
    }
    setPendingPreview(result);
  };

  const handleConfirm = () => {
    if (!pendingPreview) return;
    confirm.mutate(pendingPreview);
    setPendingPreview(null);
  };

  return (
    <div className="bg-surface-800 border border-surface-700 p-4 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h3 className="font-mono text-sm uppercase text-cyan-glow">Revisión de precios (Amazon)</h3>
        <label className="flex items-center gap-2 text-xs font-mono uppercase">
          <input
            type="checkbox"
            checked={task.enabled}
            onChange={(e) => update.mutate({ id: task.id, data: { enabled: e.target.checked } })}
          />
          Activada
        </label>
      </div>

      <div className="grid sm:grid-cols-3 gap-3">
        <label className="text-xs font-mono uppercase text-muted-foreground">
          Frecuencia
          <select
            value={task.frequency_preset}
            onChange={(e) =>
              update.mutate({
                id: task.id,
                data: { frequency_preset: e.target.value as ScheduledTaskConfig["frequency_preset"] },
              })
            }
            className="mt-1 w-full bg-surface-900 border border-surface-700 px-3 py-2 text-sm outline-none focus:border-cyan-glow"
          >
            {Object.entries(FREQUENCY_LABEL).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>

        <label className="text-xs font-mono uppercase text-muted-foreground">
          Hora (0-23)
          <input
            type="number"
            min={0}
            max={23}
            value={task.run_hour}
            onChange={(e) =>
              update.mutate({ id: task.id, data: { run_hour: Number(e.target.value) } })
            }
            className="mt-1 w-full bg-surface-900 border border-surface-700 px-3 py-2 text-sm outline-none focus:border-cyan-glow"
          />
        </label>

        <label className="text-xs font-mono uppercase text-muted-foreground">
          Tolerancia de precio (%)
          <input
            type="number"
            min={0}
            max={100}
            value={tolerance}
            onChange={(e) =>
              update.mutate({
                id: task.id,
                data: { config: { ...task.config, price_tolerance_percent: Number(e.target.value) } },
              })
            }
            className="mt-1 w-full bg-surface-900 border border-surface-700 px-3 py-2 text-sm outline-none focus:border-cyan-glow"
          />
        </label>
      </div>

      <div className="flex items-center justify-between flex-wrap gap-3 text-xs font-mono text-muted-foreground">
        <span>
          Última ejecución:{" "}
          {task.last_run_at ? new Date(task.last_run_at).toLocaleString("es-ES") : "nunca"}
        </span>
        <button
          type="button"
          onClick={handleRunNow}
          disabled={preview.isPending}
          className="bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2 flex items-center gap-2 hover:bg-foreground disabled:opacity-50"
        >
          <Play className="size-4" /> {preview.isPending ? "REVISANDO..." : "EJECUTAR AHORA"}
        </button>
      </div>

      <AlertDialog open={!!pendingPreview} onOpenChange={(open) => !open && setPendingPreview(null)}>
        <AlertDialogContent className="max-w-2xl">
          <AlertDialogHeader>
            <AlertDialogTitle>
              Se van a borrar {pendingPreview?.candidates.length ?? 0} chollo(s), ¿deseas continuar?
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="max-h-80 overflow-y-auto mt-2">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs uppercase text-muted-foreground">
                    <tr>
                      <th className="p-2">Título</th>
                      <th className="p-2">Tienda</th>
                      <th className="p-2">Precio</th>
                      <th className="p-2">Motivo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pendingPreview?.candidates.map((c) => (
                      <tr key={c.deal_id} className="border-t border-surface-700">
                        <td className="p-2">{c.title}</td>
                        <td className="p-2">{c.store_name ?? "—"}</td>
                        <td className="p-2">
                          {formatPrice(c.old_price)}
                          {c.new_price != null && <> → {formatPrice(c.new_price)}</>}
                        </td>
                        <td className="p-2">{REASON_LABEL[c.reason]}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirm}>Eliminar</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
```

- [ ] **Step 3: Write the route**

Create `buenchollo-web/src/routes/admin.tareas-programadas.tsx`:

```tsx
import { createFileRoute } from "@tanstack/react-router";
import { Skeleton } from "@/components/ui/skeleton";
import { useScheduledTasksConfig } from "@/features/admin/hooks/useScheduledTasks";
import { ScheduledTaskConfigPanel } from "@/features/admin/components/ScheduledTaskConfigPanel";
import { ScheduledTaskRunsPanel } from "@/features/admin/components/ScheduledTaskRunsPanel";

export const Route = createFileRoute("/admin/tareas-programadas")({
  component: AdminScheduledTasks,
});

function AdminScheduledTasks() {
  const { data: tasks, isLoading, isError } = useScheduledTasksConfig();
  const priceCheckTask = tasks?.find((t) => t.task_type === "price_check");

  return (
    <div className="space-y-6">
      <h2 className="font-mono text-sm uppercase text-cyan-glow">Tareas programadas</h2>

      {isLoading ? (
        <Skeleton className="h-40 w-full" />
      ) : isError || !priceCheckTask ? (
        <div className="text-center py-12 border border-red-500/30 bg-red-500/5 text-red-400">
          Error al cargar la configuración.
        </div>
      ) : (
        <>
          <ScheduledTaskConfigPanel task={priceCheckTask} />
          <ScheduledTaskRunsPanel taskId={priceCheckTask.id} />
        </>
      )}
    </div>
  );
}
```

Note: `ScheduledTaskRunsPanel` is created in Task 13 — this route file references it now so Task 13 can be reviewed as a drop-in addition; the app will not compile between Task 12 and Task 13, which is expected and resolved by the next task.

- [ ] **Step 4: Typecheck (expected to fail until Task 13)**

Run: `cd buenchollo-web && npx tsc --noEmit`
Expected: error only about missing `@/features/admin/components/ScheduledTaskRunsPanel` — no other new errors. Do not attempt to fix this in this task; Task 13 resolves it.

- [ ] **Step 5: Commit**

```bash
git add buenchollo-web/src/routes/admin.tsx buenchollo-web/src/features/admin/components/ScheduledTaskConfigPanel.tsx buenchollo-web/src/routes/admin.tareas-programadas.tsx
git commit -m "feat: add scheduled tasks nav entry, route and config panel"
```

---

### Task 13: Runs table + run detail with restore

**Files:**
- Create: `buenchollo-web/src/features/admin/components/ScheduledTaskRunsPanel.tsx`
- Create: `buenchollo-web/src/features/admin/components/ScheduledTaskRunDetailDialog.tsx`

**Interfaces:**
- Consumes: `useScheduledTaskRuns`, `useDeleteScheduledTaskRun`, `useBulkDeleteScheduledTaskRuns`, `useScheduledTaskRunDetail`, `useRestoreScheduledTaskItem` (Task 11), `ScheduledTaskRun`/`ScheduledTaskRunItem` types (Task 10), `Checkbox` (`src/components/ui/checkbox.tsx`), `AlertDialog*`, `formatPrice`/`formatRelativeTime` (`src/lib/format.ts`).
- Produces: `ScheduledTaskRunsPanel({ taskId })` — completes the import used in Task 12's route.

- [ ] **Step 1: Write the run detail dialog**

Create `buenchollo-web/src/features/admin/components/ScheduledTaskRunDetailDialog.tsx`:

```tsx
/** Detalle de un registro de ejecución: lista de chollos borrados + Restaurar. */
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { formatPrice } from "@/lib/format";
import type { ScheduledTaskCandidate } from "@/services/api/scheduled-tasks";
import {
  useRestoreScheduledTaskItem,
  useScheduledTaskRunDetail,
} from "@/features/admin/hooks/useScheduledTasks";

const REASON_LABEL: Record<ScheduledTaskCandidate["reason"], string> = {
  price_increase: "Subió de precio",
  no_longer_deal: "Ya no es oferta",
  out_of_stock: "Sin stock",
};

export function ScheduledTaskRunDetailDialog({
  runId,
  onClose,
}: {
  readonly runId: string | null;
  readonly onClose: () => void;
}) {
  const { data: run, isLoading } = useScheduledTaskRunDetail(runId);
  const restore = useRestoreScheduledTaskItem(runId ?? "");

  return (
    <AlertDialog open={!!runId} onOpenChange={(open) => !open && onClose()}>
      <AlertDialogContent className="max-w-3xl">
        <AlertDialogHeader>
          <AlertDialogTitle>Chollos afectados en esta ejecución</AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="max-h-96 overflow-y-auto mt-2">
              {isLoading ? (
                <p>Cargando...</p>
              ) : (
                <table className="w-full text-sm text-left">
                  <thead className="text-xs uppercase text-muted-foreground">
                    <tr>
                      <th className="p-2">Título</th>
                      <th className="p-2">Tienda</th>
                      <th className="p-2">Precio</th>
                      <th className="p-2">Motivo</th>
                      <th className="p-2">Acción</th>
                    </tr>
                  </thead>
                  <tbody>
                    {run?.items.map((item) => (
                      <tr key={item.id} className="border-t border-surface-700">
                        <td className="p-2">{item.title}</td>
                        <td className="p-2">{item.store_name ?? "—"}</td>
                        <td className="p-2">
                          {formatPrice(item.old_price)}
                          {item.new_price != null && <> → {formatPrice(item.new_price)}</>}
                        </td>
                        <td className="p-2">{REASON_LABEL[item.reason]}</td>
                        <td className="p-2">
                          {item.restored_at ? (
                            <span className="text-muted-foreground text-xs">Restaurado</span>
                          ) : (
                            <button
                              type="button"
                              onClick={() => restore.mutate(item.id)}
                              disabled={restore.isPending}
                              className="text-cyan-glow text-xs font-mono uppercase hover:underline disabled:opacity-50"
                            >
                              Restaurar
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cerrar</AlertDialogCancel>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

- [ ] **Step 2: Write the runs panel (table + multi-select + bulk delete)**

Create `buenchollo-web/src/features/admin/components/ScheduledTaskRunsPanel.tsx`:

```tsx
/** Listado de registros de ejecución de una tarea programada, con selección
 *  múltiple para borrado en bloque y acceso al detalle de cada uno. */
import { useState } from "react";
import { Trash2 } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { formatRelativeTime } from "@/lib/format";
import {
  useBulkDeleteScheduledTaskRuns,
  useDeleteScheduledTaskRun,
  useScheduledTaskRuns,
} from "@/features/admin/hooks/useScheduledTasks";
import { ScheduledTaskRunDetailDialog } from "@/features/admin/components/ScheduledTaskRunDetailDialog";

const TRIGGER_LABEL = { manual: "Manual", automatic: "Automática" } as const;

export function ScheduledTaskRunsPanel({ taskId }: { readonly taskId: string }) {
  const { data: runs, isLoading } = useScheduledTaskRuns(taskId);
  const deleteRun = useDeleteScheduledTaskRun(taskId);
  const bulkDelete = useBulkDeleteScheduledTaskRuns(taskId);

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [detailRunId, setDetailRunId] = useState<string | null>(null);
  const [confirmBulkDelete, setConfirmBulkDelete] = useState(false);

  const allSelected = !!runs?.length && runs.every((r) => selected.has(r.id));

  const toggleAll = () => {
    if (!runs) return;
    setSelected(allSelected ? new Set() : new Set(runs.map((r) => r.id)));
  };

  const toggleOne = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleBulkDelete = () => {
    bulkDelete.mutate(Array.from(selected));
    setSelected(new Set());
    setConfirmBulkDelete(false);
  };

  if (isLoading) return <p className="text-sm text-muted-foreground">Cargando registros...</p>;

  return (
    <div className="bg-surface-800 border border-surface-700 overflow-x-auto">
      <div className="flex items-center justify-between p-3 border-b border-surface-700">
        <h3 className="font-mono text-sm uppercase text-cyan-glow">Registro de ejecuciones</h3>
        {selected.size > 0 && (
          <button
            type="button"
            onClick={() => setConfirmBulkDelete(true)}
            className="flex items-center gap-2 text-xs font-mono uppercase text-alert-red hover:underline"
          >
            <Trash2 className="size-4" /> Eliminar {selected.size} seleccionado(s)
          </button>
        )}
      </div>
      <table className="w-full text-sm">
        <thead className="border-b border-surface-700 font-mono text-xs uppercase text-muted-foreground">
          <tr>
            <th className="p-3 w-10">
              <Checkbox checked={allSelected} onCheckedChange={toggleAll} aria-label="Seleccionar todos" />
            </th>
            <th className="text-left p-3">Fecha</th>
            <th className="text-left p-3">Tipo</th>
            <th className="text-right p-3">Revisados</th>
            <th className="text-right p-3">Borrados</th>
            <th className="p-3">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {runs?.map((run) => (
            <tr key={run.id} className="border-b border-surface-700/50 hover:bg-surface-700/30">
              <td className="p-3">
                <Checkbox
                  checked={selected.has(run.id)}
                  onCheckedChange={() => toggleOne(run.id)}
                  aria-label={`Seleccionar registro del ${run.started_at}`}
                />
              </td>
              <td className="p-3 text-muted-foreground font-mono text-xs">
                {formatRelativeTime(run.started_at)}
              </td>
              <td className="p-3 font-mono text-xs uppercase">{TRIGGER_LABEL[run.trigger_type]}</td>
              <td className="p-3 text-right font-mono">{run.total_checked}</td>
              <td className="p-3 text-right font-mono text-alert-red">{run.total_affected}</td>
              <td className="p-3 flex gap-1">
                <button
                  type="button"
                  onClick={() => setDetailRunId(run.id)}
                  className="text-xs font-mono uppercase text-cyan-glow hover:underline"
                >
                  Ver
                </button>
                <button
                  type="button"
                  onClick={() => deleteRun.mutate(run.id)}
                  className="p-1 hover:text-alert-red"
                  title="Eliminar registro"
                >
                  <Trash2 className="size-4" />
                </button>
              </td>
            </tr>
          ))}
          {runs?.length === 0 && (
            <tr>
              <td colSpan={6} className="p-6 text-center text-muted-foreground font-mono text-xs">
                SIN_EJECUCIONES
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <ScheduledTaskRunDetailDialog runId={detailRunId} onClose={() => setDetailRunId(null)} />

      <AlertDialog open={confirmBulkDelete} onOpenChange={setConfirmBulkDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Eliminar {selected.size} registro(s)</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción eliminará permanentemente los registros seleccionados. No se puede deshacer.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleBulkDelete}>Eliminar</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
```

- [ ] **Step 3: Typecheck**

Run: `cd buenchollo-web && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Manual verification in the browser**

Run: `cd buenchollo-web && npm run dev` (regenerates `routeTree.gen.ts` automatically).
Open `/admin/tareas-programadas` as an admin user and verify:
- The config panel loads with the seeded `price_check` task (disabled, weekly, hour 4, tolerance 10).
- Toggling "Activada", changing frequency/hour/tolerance persists (check network tab / reload).
- "Ejecutar ahora" with zero candidates shows no dialog (silently does nothing) — need at least one active deal without `expires_at` and with a valid ASIN to see the confirmation dialog; with real Amazon credentials this hits the live API, so verify at minimum that the button doesn't crash and errors surface as a toast if Amazon credentials are missing.
- The runs table renders, checkboxes select/deselect, "seleccionar todos" works, bulk delete shows a confirmation and removes rows.
- Clicking "Ver" opens the detail dialog with the items table; "Restaurar" on an item creates a new active deal and the button becomes "Restaurado".
- Check mobile width (375px) and desktop width — no horizontal overflow (per `CLAUDE.md` §5).

- [ ] **Step 5: Commit**

```bash
git add buenchollo-web/src/features/admin/components/ScheduledTaskRunsPanel.tsx buenchollo-web/src/features/admin/components/ScheduledTaskRunDetailDialog.tsx
git commit -m "feat: add scheduled task runs table and restore dialog"
```

---

## Post-implementation notes (not tasks — read before wrapping up)

- **Deuda técnica / OPTIMIZACION_PLAN.md**: per `CLAUDE.md`, remind the user briefly about pending technical debt (`docs/project/10-technical-debt.md`, currently empty) and the performance plan (`OPTIMIZACION_PLAN.md`) when switching away from this task.
- **Deployment**: the new `run_scheduled_tasks` job runs inside the existing `buenchollo-scheduler` container — no new container or docker-compose change needed. The migration runs automatically on next deploy (`alembic upgrade head` in the Dockerfile's start command).
- **Amazon credentials in dev**: `preview`/`confirm`/automatic runs require `AMAZON_CLIENT_ID`/`AMAZON_CLIENT_SECRET` configured — without them `AmazonProductClient` raises `ProductProviderUnavailableError`, which is a `DomainError` (503) and will surface as a toast on the frontend, not a crash.
