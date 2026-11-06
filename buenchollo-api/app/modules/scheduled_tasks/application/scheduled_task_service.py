import logging
from datetime import datetime, timedelta, timezone
from typing import Literal

from app.core.audit import audit_log
from app.modules.scheduled_tasks.application.task_handler import Candidate, PreviewResult, TaskHandler
from app.modules.scheduled_tasks.domain.exceptions import ScheduledTaskNotFound, TaskAlreadyRunningError
from app.modules.scheduled_tasks.domain.models import ScheduledTask, ScheduledTaskRun, ScheduledTaskRunItem

logger = logging.getLogger(__name__)

FREQUENCY_DAYS = {"daily": 1, "weekly": 7, "biweekly": 14, "monthly": 30}


def is_task_due(task: ScheduledTask, now: datetime) -> bool:
    """`now` debe representar ya la hora local del servidor (el caller hace
    la conversión desde UTC, ver scheduler.py) — aquí se compara tal cual,
    para que el test no dependa de la zona horaria de la máquina que lo
    ejecuta.

    Se comparan fechas y no instantes: si ayer la tarea terminó a las 04:05,
    hoy toca a las 04:00 (comparando instantes esperaría a las 05:00 y la hora
    de ejecución se iría retrasando un tick cada día)."""
    if not task.enabled:
        return False
    if now.hour < task.run_hour:
        return False
    if task.last_run_at is None:
        return True
    last_run = task.last_run_at.astimezone(now.tzinfo) if now.tzinfo else task.last_run_at
    days = FREQUENCY_DAYS[task.frequency_preset]
    return now.date() >= last_run.date() + timedelta(days=days)


class ScheduledTaskService:
    def __init__(self, repo, handlers: dict[str, TaskHandler], session):
        self.repo = repo
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
        """Qué haría la tarea ahora mismo, sin escribir nada."""
        task = await self._get_task_or_404(task_id)
        handler = self.handlers[task.task_type]
        config = task.config
        # Sin transacción abierta mientras se consulta Amazon (PgBouncer).
        checks = await handler.collect(between=self.session.commit)
        return handler.evaluate(checks, config, datetime.now(timezone.utc))

    async def confirm(self, task_id: str, triggered_by: str) -> ScheduledTaskRun:
        """Ejecución manual desde el panel: aplica todas las transiciones."""
        return await self.run(task_id, trigger_type="manual", triggered_by=triggered_by)

    async def run_automatic(self, task_id: str) -> ScheduledTaskRun:
        return await self.run(task_id, trigger_type="automatic", triggered_by=None)

    async def run(
        self, task_id: str, *, trigger_type: Literal["manual", "automatic"], triggered_by: str | None
    ) -> ScheduledTaskRun:
        task = await self._get_task_or_404(task_id)
        handler = self.handlers[task.task_type]
        # Exclusión mutua worker / panel: la marca se guarda ya (commit) para que
        # la vea el otro proceso; se quita al terminar, también si falla.
        if not await self.repo.claim_run(task_id):
            raise TaskAlreadyRunningError(task_id)
        await self.session.commit()
        total_checked = 0
        try:
            # `between` cierra la transacción tras cargar el catálogo: la consulta
            # a Amazon (minutos con un catálogo grande) no retiene una conexión.
            checks = await handler.collect(between=self.session.commit)
            total_checked = len(checks)
            applied = await handler.apply(checks, task.config, datetime.now(timezone.utc))
            run = await self._persist_run(
                task, trigger_type=trigger_type, total_checked=total_checked,
                applied=applied, triggered_by=triggered_by,
            )
            task.last_run_at = datetime.now(timezone.utc)
            await self.repo.release_run(task_id)
            await self.repo.update_task(task)
            return run
        except Exception as exc:
            logger.exception("Fallo ejecutando la tarea programada %s", task_id)
            # Si la excepción vino de una operación SQLAlchemy la sesión queda en
            # estado rollback-required: sin este rollback, `create_run` fallaría
            # con PendingRollbackError y se perdería el registro del fallo. Tras
            # el rollback no se vuelve a leer el ORM (atributos expirados): se
            # usa el `task_id` recibido.
            await self.session.rollback()
            now = datetime.now(timezone.utc)
            await self.repo.create_run(
                ScheduledTaskRun(
                    task_id=task_id, trigger_type=trigger_type, status="failed",
                    started_at=now, finished_at=now, total_checked=total_checked, total_affected=0,
                    triggered_by=triggered_by, error_message=str(exc)[:500],
                )
            )
            await self.repo.release_run(task_id)
            # Se guarda ya: en la ejecución manual el rollback de la petición
            # se llevaría el registro del fallo y dejaría la marca puesta.
            await self.session.commit()
            raise

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

    async def _persist_run(self, task, *, trigger_type, total_checked, applied, triggered_by):
        now = datetime.now(timezone.utc)
        run = ScheduledTaskRun(
            task_id=task.id, trigger_type=trigger_type, status="completed",
            started_at=now, finished_at=now, total_checked=total_checked,
            total_affected=len(applied), triggered_by=triggered_by,
        )
        run.items = [self._candidate_to_item(c) for c in applied]
        created = await self.repo.create_run(run)
        for candidate in applied:
            await audit_log(
                self.session,
                user_id=triggered_by,
                action="deal.offer_transition",
                target_type="deal",
                target_id=candidate.deal_id,
                payload={
                    "transition": candidate.transition,
                    "reason": candidate.reason,
                    "old_price": float(candidate.old_price),
                    "new_price": float(candidate.new_price) if candidate.new_price is not None else None,
                },
            )
        return created

    @staticmethod
    def _candidate_to_item(candidate: Candidate) -> ScheduledTaskRunItem:
        return ScheduledTaskRunItem(
            deal_id_snapshot=candidate.deal_id,
            title=candidate.title[:200],
            slug=candidate.slug[:200],
            image_url=candidate.image_url,
            description=candidate.description,
            short_description=candidate.short_description,
            store_id=candidate.store_id,
            store_name=candidate.store_name,
            category_id=candidate.category_id,
            subcategory_id=candidate.subcategory_id,
            external_id=candidate.external_id,
            affiliate_url=candidate.affiliate_url,
            source_url=candidate.source_url,
            old_price=candidate.old_price,
            previous_price=candidate.previous_price,
            discount_percentage=candidate.discount_percentage,
            new_price=candidate.new_price,
            reason=candidate.reason,
            transition=candidate.transition,
        )
