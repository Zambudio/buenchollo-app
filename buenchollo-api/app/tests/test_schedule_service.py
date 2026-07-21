from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.scheduled_deals.application.schedule_service import ScheduleService
from app.modules.scheduled_deals.domain.models import ScheduledDealStatus


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
