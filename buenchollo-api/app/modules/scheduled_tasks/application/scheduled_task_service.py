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
