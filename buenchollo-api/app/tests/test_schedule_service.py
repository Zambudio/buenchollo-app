from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.scheduled_deals.application.schedule_service import ScheduleService
from app.modules.scheduled_deals.domain.exceptions import InvalidSchedule
from app.modules.scheduled_deals.domain.models import ScheduledDealStatus
from app.modules.scheduled_deals.infrastructure.repository import ScheduledDealRepository


@pytest.mark.asyncio
async def test_reschedule_updates_queue_and_linked_web_deal():
    now = datetime.now(timezone.utc)
    minutes_to_boundary = 5 - (now.minute % 5)
    original = (now + timedelta(minutes=minutes_to_boundary)).replace(second=0, microsecond=0)
    target = original + timedelta(days=1)
    scheduled = SimpleNamespace(
        id="schedule-id",
        deal_id="deal-id",
        status=ScheduledDealStatus.SCHEDULED,
        scheduled_at=original,
        deal=SimpleNamespace(expires_at=target + timedelta(days=1)),
    )
    repo = SimpleNamespace(
        get_by_id=AsyncMock(return_value=scheduled),
        update=AsyncMock(side_effect=lambda value: value),
    )
    deal_service = SimpleNamespace(update_deal=AsyncMock())
    service = ScheduleService(repo, deal_service)

    result = await service.reschedule("schedule-id", target)

    assert result.scheduled_at == target
    repo.update.assert_awaited_once_with(scheduled)
    deal_service.update_deal.assert_awaited_once_with(
        "deal-id", {"scheduled_for": target}
    )


@pytest.mark.asyncio
async def test_reschedule_rejects_date_after_deal_expiry():
    now = datetime.now(timezone.utc)
    target = (now + timedelta(days=2)).replace(minute=0, second=0, microsecond=0)
    scheduled = SimpleNamespace(
        id="schedule-id",
        deal_id="deal-id",
        status=ScheduledDealStatus.SCHEDULED,
        scheduled_at=now + timedelta(hours=1),
        deal=SimpleNamespace(expires_at=now + timedelta(days=1)),
    )
    repo = SimpleNamespace(get_by_id=AsyncMock(return_value=scheduled), update=AsyncMock())
    deal_service = SimpleNamespace(update_deal=AsyncMock())
    service = ScheduleService(repo, deal_service)

    with pytest.raises(InvalidSchedule, match="anterior a la caducidad"):
        await service.reschedule("schedule-id", target)

    repo.update.assert_not_awaited()
    deal_service.update_deal.assert_not_awaited()


@pytest.mark.asyncio
async def test_repository_update_refreshes_server_generated_updated_at():
    session = SimpleNamespace(flush=AsyncMock(), refresh=AsyncMock())
    scheduled = SimpleNamespace()
    repo = ScheduledDealRepository(session)

    result = await repo.update(scheduled)

    assert result is scheduled
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(scheduled, attribute_names=["updated_at"])


def test_next_slot_advances_two_hours_after_latest_schedule():
    now = datetime(2026, 7, 21, 10, 0, tzinfo=timezone.utc)
    latest = datetime(2026, 7, 24, 16, 0, tzinfo=timezone.utc)  # 18:00 Madrid

    result = ScheduleService.calculate_next_slot(latest, now)

    assert result == datetime(2026, 7, 24, 18, 0, tzinfo=timezone.utc)  # 20:00 Madrid


def test_next_slot_rolls_from_22_to_next_day_at_08():
    now = datetime(2026, 7, 21, 10, 0, tzinfo=timezone.utc)
    latest = datetime(2026, 7, 24, 20, 0, tzinfo=timezone.utc)  # 22:00 Madrid

    result = ScheduleService.calculate_next_slot(latest, now)

    assert result == datetime(2026, 7, 25, 6, 0, tzinfo=timezone.utc)  # 08:00 Madrid


@pytest.mark.asyncio
async def test_get_scheduled_deal_by_linked_web_deal_id():
    scheduled = SimpleNamespace(id="schedule-id")
    repo = SimpleNamespace(get_by_deal_id=AsyncMock(return_value=scheduled))
    service = ScheduleService(repo, SimpleNamespace())

    result = await service.get_by_deal_id("deal-id")

    assert result is scheduled
    repo.get_by_deal_id.assert_awaited_once_with("deal-id")
