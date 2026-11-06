"""Factory for registering and creating scheduled task handlers."""
from typing import Mapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.modules.alerts.application.alert_matcher import AlertMatcher
from app.modules.alerts.infrastructure.repository import AlertRepository
from app.modules.catalog.application.reactivation_notifier import ReactivationNotifier
from app.modules.catalog.infrastructure.repository import CatalogRepository
from app.modules.deals.infrastructure.repository import DealRepository
from app.modules.notifications.infrastructure.repository import NotificationRepository
from app.modules.products.infrastructure.amazon_client import AmazonProductClient
from app.modules.scheduled_tasks.application.price_check_handler import PriceCheckHandler
from app.modules.scheduled_tasks.application.task_handler import TaskHandler
from app.modules.telegram.application.post_generator import TelegramPostGenerator
from app.modules.telegram.infrastructure.publication_repository import TelegramPublicationRepository
from app.modules.telegram.infrastructure.telegram_bot import TelegramBot


def build_task_handlers(session: AsyncSession, settings: Settings) -> Mapping[str, TaskHandler]:
    """Build the registry mapping of task_type -> TaskHandler instance.

    Centralizes handler instantiation for both the FastAPI router (manual execution)
    and the background APScheduler worker (automatic execution).
    """
    return {
        "price_check": PriceCheckHandler(AmazonProductClient(settings), CatalogRepository(session)),
    }


def build_reactivation_notifier(session: AsyncSession, settings: Settings) -> ReactivationNotifier:
    """Aviso de reactivaciones al canal Admin, compartido por el panel
    (ejecución manual) y el worker (ejecución automática)."""
    return ReactivationNotifier(
        bot=TelegramBot(settings.telegram_bot_token),
        admin_chat_id=settings.telegram_admin_channel_id,
        matcher=AlertMatcher(AlertRepository(session), NotificationRepository(session)),
        deal_repo=DealRepository(session),
        site_url=settings.public_site_url,
        publications=TelegramPublicationRepository(session),
        generator=TelegramPostGenerator(settings=settings),
    )
