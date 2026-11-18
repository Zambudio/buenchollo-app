"""Casos de uso de alertas de usuario."""
from app.modules.alerts.domain.exceptions import AlertLimitReached
from app.modules.alerts.domain.models import Alert
from app.modules.alerts.infrastructure.repository import AlertRepository

MAX_ALERTS_PER_USER = 50


async def create_alert_for_user(repo: AlertRepository, user_id: str, data: dict) -> Alert:
    """Crea una alerta respetando el tope por usuario."""
    if await repo.count_by_user(user_id) >= MAX_ALERTS_PER_USER:
        raise AlertLimitReached(MAX_ALERTS_PER_USER)
    return await repo.create(user_id, data)
