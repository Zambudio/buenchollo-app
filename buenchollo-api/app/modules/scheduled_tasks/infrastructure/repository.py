from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.scheduled_tasks.domain.models import (
    ScheduledTask,
    ScheduledTaskRun,
)


class ScheduledTaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # --- ScheduledTask (config) ---

    async def claim_run(self, task_id: str, stale_after: timedelta = timedelta(minutes=30)) -> bool:
        """Marca la tarea como en curso si nadie la tiene (o la marca es de un
        proceso que murió hace más de `stale_after`). UPDATE atómico: entre el
        worker y "Ejecutar ahora" del panel solo uno lo consigue."""
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            update(ScheduledTask)
            .where(
                ScheduledTask.id == task_id,
                or_(ScheduledTask.running_since.is_(None), ScheduledTask.running_since < now - stale_after),
            )
            .values(running_since=now)
            .returning(ScheduledTask.id)
            .execution_options(synchronize_session=False)
        )
        return result.first() is not None

    async def release_run(self, task_id: str) -> None:
        await self.session.execute(
            update(ScheduledTask)
            .where(ScheduledTask.id == task_id)
            .values(running_since=None)
            .execution_options(synchronize_session=False)
        )

    async def get_by_id(self, task_id: str) -> ScheduledTask | None:
        result = await self.session.execute(select(ScheduledTask).where(ScheduledTask.id == task_id))
        return result.scalars().first()

    async def list_tasks(self) -> list[ScheduledTask]:
        result = await self.session.execute(select(ScheduledTask).order_by(ScheduledTask.task_type))
        return list(result.scalars().all())

    async def get_enabled_tasks(self) -> list[ScheduledTask]:
        result = await self.session.execute(select(ScheduledTask).where(ScheduledTask.enabled == True))
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
