"""Aviso al canal Admin de Telegram (y alertas de usuario) cuando una oferta
vuelve a estar activa tras la revisión diaria. No publica en el canal oficial:
Pedro decide desde el canal Admin si la reenvía.

Antispam: un aviso por deal cada 7 días, salvo que el precio sea menor que el
del último aviso. Un fallo de Telegram nunca deshace la reactivación.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from starlette.concurrency import run_in_threadpool

from app.modules.telegram.application.post_generator import _format_price_es

logger = logging.getLogger(__name__)

ADMIN_COOLDOWN = timedelta(days=7)


def should_notify(
    notified_at: datetime | None, notified_price: Decimal | None, price: Decimal, now: datetime
) -> bool:
    if notified_at is None or notified_price is None:
        return True
    if now - notified_at >= ADMIN_COOLDOWN:
        return True
    return Decimal(str(price)) < Decimal(str(notified_price))


def build_admin_message(deal, site_url: str) -> str:
    price_line = f"💶 {_format_price_es(float(deal.current_price))} €"
    if deal.previous_price is not None:
        price_line += f" (antes {_format_price_es(float(deal.previous_price))} €"
        if deal.discount_percentage:
            price_line += f", -{deal.discount_percentage} %"
        price_line += ")"
    store_name = deal.store.name if deal.store else "Tienda"
    return "\n".join(
        [
            "🔁 Vuelve a estar en oferta",
            deal.title,
            price_line,
            f"🏪 {store_name}",
            f"🛒 {deal.affiliate_url}",
            f"🌐 {site_url.rstrip('/')}/chollo/{deal.slug}",
        ]
    )


def reactivated_deal_ids(run) -> list[str]:
    return [item.deal_id_snapshot for item in run.items if item.transition == "reactivated"]


class ReactivationNotifier:
    def __init__(self, bot, admin_chat_id: str, matcher, deal_repo, site_url: str):
        self.bot = bot
        self.admin_chat_id = admin_chat_id
        self.matcher = matcher
        self.deal_repo = deal_repo
        self.site_url = site_url

    async def notify(self, deal_ids: list[str], now: datetime) -> int:
        """Devuelve cuántos avisos llegaron al canal Admin."""
        sent = 0
        for deal_id in deal_ids:
            deal = await self.deal_repo.get_by_id(deal_id)
            if deal is None or deal.status != "active":
                continue
            if not should_notify(deal.admin_notified_at, deal.admin_notified_price, deal.current_price, now):
                continue
            await self.matcher.notify_matching_alerts(deal)
            if not self.admin_chat_id:
                logger.info("Reactivación de %s sin canal Admin configurado: no se avisa", deal.slug)
                continue
            if await self._send(build_admin_message(deal, self.site_url)):
                deal.admin_notified_at = now
                deal.admin_notified_price = deal.current_price
                sent += 1
        return sent

    async def _send(self, text: str) -> bool:
        try:
            return bool(
                await run_in_threadpool(self.bot.send_admin_notification, text, chat_id=self.admin_chat_id)
            )
        except Exception:
            logger.exception("Fallo avisando al canal Admin de una reactivación")
            return False
