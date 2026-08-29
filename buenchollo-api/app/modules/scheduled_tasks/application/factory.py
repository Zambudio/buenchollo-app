"""Factory for registering and creating scheduled task handlers."""
from typing import Mapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.modules.deals.infrastructure.repository import DealRepository
from app.modules.products.infrastructure.amazon_client import AmazonProductClient
from app.modules.scheduled_tasks.application.price_check_handler import PriceCheckHandler
from app.modules.scheduled_tasks.application.task_handler import TaskHandler


def build_task_handlers(session: AsyncSession, settings: Settings) -> Mapping[str, TaskHandler]:
    """Build the registry mapping of task_type -> TaskHandler instance.

    Centralizes handler instantiation for both the FastAPI router (manual execution)
    and the background APScheduler worker (automatic execution).
    """
    deal_repo = DealRepository(session)
    amazon_client = AmazonProductClient(settings)

    return {
        "price_check": PriceCheckHandler(amazon_client, deal_repo),
    }
