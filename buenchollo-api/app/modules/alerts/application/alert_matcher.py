import logging
from app.modules.alerts.infrastructure.repository import AlertRepository
from app.modules.deals.domain.models import Deal
from app.modules.notifications.infrastructure.repository import NotificationRepository

logger = logging.getLogger(__name__)


class AlertMatcher:
    def __init__(self, alerts: AlertRepository, notifications: NotificationRepository):
        self.alerts = alerts
        self.notifications = notifications

    async def notify_matching_alerts(self, deal: Deal) -> int:
        if deal.status != "active":
            return 0

        matches = await self.alerts.get_matching_for_deal(deal)
        created = 0

        for alert in matches:
            if await self.notifications.exists_for_alert_deal(alert.id, deal.id):
                continue
            await self.notifications.create(
                {
                    "user_id": alert.user_id,
                    "type": "alert_match",
                    "title": f"Radar activado: {alert.name}",
                    "body": f"Nuevo chollo: {deal.title}",
                    "link_url": f"/chollo/{deal.slug}",
                    "deal_id": deal.id,
                    "alert_id": alert.id,
                }
            )
            await self.alerts.mark_triggered(alert)
            created += 1

        if created:
            logger.info("Alertas: %d notificacion(es) creadas para deal_id=%s", created, deal.id)
        return created
