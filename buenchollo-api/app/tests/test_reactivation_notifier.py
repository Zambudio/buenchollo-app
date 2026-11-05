from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.catalog.application.reactivation_notifier import (
    ReactivationNotifier,
    build_admin_message,
    reactivated_deal_ids,
    should_notify,
)

NOW = datetime(2026, 11, 5, 4, 0, tzinfo=timezone.utc)


def _deal(**overrides):
    base = dict(
        id="deal-1", title="Monitor LG 27GP850", slug="monitor-lg-27gp850",
        current_price=Decimal("289.9"), previous_price=Decimal("449"), discount_percentage=35,
        store=SimpleNamespace(name="Amazon"), affiliate_url="https://www.amazon.es/dp/B0X?tag=bct-21",
        admin_notified_at=None, admin_notified_price=None, status="active",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


# --- should_notify ---


def test_should_notify_nunca_avisado():
    assert should_notify(None, None, Decimal("10"), NOW) is True


def test_should_notify_6_dias_mismo_precio_no():
    assert should_notify(NOW - timedelta(days=6), Decimal("10"), Decimal("10"), NOW) is False


def test_should_notify_6_dias_precio_menor_si():
    assert should_notify(NOW - timedelta(days=6), Decimal("10"), Decimal("9.99"), NOW) is True


def test_should_notify_7_dias_si():
    assert should_notify(NOW - timedelta(days=7), Decimal("10"), Decimal("12"), NOW) is True


# --- build_admin_message ---


def test_build_admin_message_con_precio_anterior():
    assert build_admin_message(_deal(), "https://buenchollotech.com") == (
        "🔁 Vuelve a estar en oferta\n"
        "Monitor LG 27GP850\n"
        "💶 289,90 € (antes 449,00 €, -35 %)\n"
        "🏪 Amazon\n"
        "🛒 https://www.amazon.es/dp/B0X?tag=bct-21\n"
        "🌐 https://buenchollotech.com/chollo/monitor-lg-27gp850"
    )


def test_build_admin_message_sin_precio_anterior_ni_tienda():
    deal = _deal(previous_price=None, discount_percentage=None, store=None)
    assert build_admin_message(deal, "https://buenchollotech.com/") == (
        "🔁 Vuelve a estar en oferta\n"
        "Monitor LG 27GP850\n"
        "💶 289,90 €\n"
        "🏪 Tienda\n"
        "🛒 https://www.amazon.es/dp/B0X?tag=bct-21\n"
        "🌐 https://buenchollotech.com/chollo/monitor-lg-27gp850"
    )


# --- reactivated_deal_ids ---


def test_reactivated_deal_ids_filtra_por_transicion():
    run = SimpleNamespace(items=[
        SimpleNamespace(transition="reactivated", deal_id_snapshot="a"),
        SimpleNamespace(transition="offer_ended", deal_id_snapshot="b"),
        SimpleNamespace(transition="reactivated", deal_id_snapshot="c"),
    ])
    assert reactivated_deal_ids(run) == ["a", "c"]


# --- notify ---


def _notifier(deal, *, sent=True, chat_id="-100admin"):
    bot = MagicMock()
    bot.send_admin_notification = MagicMock(return_value=sent)
    matcher = MagicMock()
    matcher.notify_matching_alerts = AsyncMock(return_value=1)
    deal_repo = MagicMock()
    deal_repo.get_by_id = AsyncMock(return_value=deal)
    return ReactivationNotifier(bot, chat_id, matcher, deal_repo, "https://buenchollotech.com"), bot, matcher


@pytest.mark.asyncio
async def test_notify_envia_y_marca_antispam():
    deal = _deal()
    notifier, bot, matcher = _notifier(deal)

    sent = await notifier.notify(["deal-1"], NOW)

    assert sent == 1
    bot.send_admin_notification.assert_called_once()
    assert bot.send_admin_notification.call_args.kwargs["chat_id"] == "-100admin"
    matcher.notify_matching_alerts.assert_awaited_once_with(deal)
    assert deal.admin_notified_at == NOW
    assert deal.admin_notified_price == Decimal("289.9")


@pytest.mark.asyncio
async def test_notify_fallo_de_telegram_no_lanza_ni_marca():
    deal = _deal()
    notifier, _, _ = _notifier(deal, sent=False)

    assert await notifier.notify(["deal-1"], NOW) == 0
    assert deal.admin_notified_at is None


@pytest.mark.asyncio
async def test_notify_excepcion_de_telegram_no_lanza():
    deal = _deal()
    notifier, bot, _ = _notifier(deal)
    bot.send_admin_notification.side_effect = RuntimeError("red caída")

    assert await notifier.notify(["deal-1"], NOW) == 0
    assert deal.admin_notified_at is None


@pytest.mark.asyncio
async def test_notify_con_cooldown_no_avisa_ni_dispara_alertas():
    deal = _deal(admin_notified_at=NOW - timedelta(days=2), admin_notified_price=Decimal("289.9"))
    notifier, bot, matcher = _notifier(deal)

    assert await notifier.notify(["deal-1"], NOW) == 0
    bot.send_admin_notification.assert_not_called()
    matcher.notify_matching_alerts.assert_not_awaited()


@pytest.mark.asyncio
async def test_notify_sin_canal_configurado_solo_dispara_alertas():
    deal = _deal()
    notifier, bot, matcher = _notifier(deal, chat_id="")

    assert await notifier.notify(["deal-1"], NOW) == 0
    bot.send_admin_notification.assert_not_called()
    matcher.notify_matching_alerts.assert_awaited_once_with(deal)
    assert deal.admin_notified_at is None


@pytest.mark.asyncio
async def test_notify_ignora_deals_borrados_o_no_activos():
    notifier, bot, _ = _notifier(None)
    assert await notifier.notify(["x"], NOW) == 0
    notifier, bot, _ = _notifier(_deal(status="expired"))
    assert await notifier.notify(["deal-1"], NOW) == 0
    bot.send_admin_notification.assert_not_called()
