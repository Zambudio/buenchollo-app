"""Aviso al canal Admin cuando un chollo vuelve a estar en oferta o baja de precio.

Petición de Pedro (2026-11-06): dos mensajes. Primero el aviso (qué ha pasado,
precio de antes y de ahora) y después la publicación de Telegram que se envió
la última vez, con el precio corregido, lista para volver a publicarla.

Petición de Pedro (2026-11-18): solo avisar de chollos publicados hace al menos
10 días (última publicación en Telegram o, si no la hay, alta en la web) e
indicar en el aviso cuándo se publicó.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.catalog.application.reactivation_notifier import (
    LastPublication,
    OfferEvent,
    ReactivationNotifier,
    build_admin_message,
    notifiable_events,
    should_notify,
)
from app.modules.telegram.application.post_generator import TelegramPostGenerator

NOW = datetime(2026, 11, 6, 4, 0, tzinfo=timezone.utc)
SITE = "https://buenchollotech.com"


def _deal(**overrides):
    base = dict(
        id="deal-1", title="Monitor LG 27GP850", slug="monitor-lg-27gp850",
        current_price=Decimal("289.9"), previous_price=Decimal("449"), discount_percentage=35,
        store=SimpleNamespace(name="Amazon"), affiliate_url="https://www.amazon.es/dp/B0X?tag=bct-21",
        image_url="https://img/deal.jpg", short_description="Monitor gaming", expires_at=None,
        admin_notified_at=None, admin_notified_price=None, status="active",
        created_at=NOW - timedelta(days=30),
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


# --- mensaje de aviso ---

ON_TELEGRAM = LastPublication(datetime(2026, 10, 20, 9, 30, tzinfo=timezone.utc), on_telegram=True)


def test_aviso_de_reactivacion():
    event = OfferEvent("deal-1", "reactivated", Decimal("299.90"))
    assert build_admin_message(_deal(), event, SITE, ON_TELEGRAM, NOW) == (
        "🔁 Vuelve a estar en oferta\n"
        "Monitor LG 27GP850\n"
        "💶 Ahora 289,90 € · la última vez que fue chollo: 299,90 €\n"
        "🗓️ Última publicación en Telegram: 20/10/2026 (hace 16 días)\n"
        "🏷️ Referencia de la tienda: 449,00 € (-35 %)\n"
        "🏪 Amazon\n"
        "🌐 https://buenchollotech.com/chollo/monitor-lg-27gp850\n"
        "👇 Publicación con el precio corregido, lista para reenviar (comprueba antes que sigue siendo buena oferta)"
    )


def test_aviso_de_bajada_sin_referencia_de_tienda():
    event = OfferEvent("deal-1", "price_dropped", Decimal("320"))
    only_web = LastPublication(NOW - timedelta(days=12), on_telegram=False)
    text = build_admin_message(_deal(previous_price=None, store=None), event, SITE + "/", only_web, NOW)
    assert text.startswith(
        "📉 Ha bajado de precio\nMonitor LG 27GP850\n💶 Ahora 289,90 € · antes 320,00 €\n"
        "🗓️ Publicado en la web (nunca en Telegram): 25/10/2026 (hace 12 días)\n🏪 Tienda\n"
    )
    assert "Referencia" not in text


def test_notifiable_events_desde_el_registro():
    run = SimpleNamespace(items=[
        SimpleNamespace(transition="reactivated", deal_id_snapshot="a", old_price=Decimal("10")),
        SimpleNamespace(transition="offer_ended", deal_id_snapshot="b", old_price=Decimal("20")),
        SimpleNamespace(transition="price_dropped", deal_id_snapshot="c", old_price=Decimal("30")),
    ])
    assert notifiable_events(run) == [
        OfferEvent("a", "reactivated", Decimal("10")), OfferEvent("c", "price_dropped", Decimal("30")),
    ]


# --- notify ---


def _notifier(deal, *, publication=None, notice_ok=True, post_ok=True, chat_id="-100admin"):
    bot = MagicMock()
    bot.send_admin_notification = MagicMock(return_value=notice_ok)
    bot.send_preformatted = MagicMock(return_value=post_ok)
    matcher = MagicMock()
    matcher.notify_matching_alerts = AsyncMock(return_value=1)
    deal_repo = MagicMock()
    deal_repo.get_by_id = AsyncMock(return_value=deal)
    publications = MagicMock()
    publications.latest_for_deal = AsyncMock(return_value=publication)
    notifier = ReactivationNotifier(
        bot, chat_id, matcher, deal_repo, SITE,
        publications=publications, generator=TelegramPostGenerator(ai_service=object()),
    )
    return notifier, bot, matcher


EVENT = OfferEvent("deal-1", "reactivated", Decimal("299.90"))


@pytest.mark.asyncio
async def test_envia_aviso_y_despues_la_publicacion_anterior_corregida():
    original = TelegramPostGenerator(ai_service=object()).generate_text(
        title="Monitor LG", current_price=299.90, previous_price=449, discount_pct=33,
        description="Mi texto del panel", affiliate_url="https://amzn.to/abc",
    )
    publication = SimpleNamespace(text=original, image_url="https://img/publicada.jpg", sent_at=NOW - timedelta(days=11))
    deal = _deal()
    notifier, bot, matcher = _notifier(deal, publication=publication)

    assert await notifier.notify([EVENT], NOW) == 1

    bot.send_admin_notification.assert_called_once()
    post, whatsapp = (call.kwargs for call in bot.send_preformatted.call_args_list)
    assert post["chat_id"] == "-100admin"
    assert post["image_url"] == "https://img/publicada.jpg"
    # Segundo envío: la versión WhatsApp, en texto plano y con la misma imagen
    assert whatsapp["chat_id"] == "-100admin" and whatsapp["entities"] == []
    assert whatsapp["image_url"] == "https://img/publicada.jpg"
    assert "🏷️ *Precio: 289,90 € (antes 449,00 €)*" in whatsapp["text"]
    assert whatsapp["text"].endswith("https://buenchollotech.com/whatsapp")
    assert "💶 Precio: 289,90 € (antes 449,00 €)" in post["text"]
    assert "Mi texto del panel" in post["text"] and "299,90" not in post["text"]
    assert any(e["type"] == "bold" for e in post["entities"])
    matcher.notify_matching_alerts.assert_awaited_once_with(deal)
    assert deal.admin_notified_at == NOW and deal.admin_notified_price == Decimal("289.9")


@pytest.mark.asyncio
async def test_sin_publicacion_anterior_genera_una_nueva():
    notifier, bot, _ = _notifier(_deal(), publication=None)

    await notifier.notify([EVENT], NOW)

    post = bot.send_preformatted.call_args_list[0].kwargs
    assert post["text"].startswith("🍄 Monitor LG 27GP850\n\n💶 Precio: 289,90 € (antes 449,00 €)")
    assert "https://www.amazon.es/dp/B0X?tag=bct-21" in post["text"]
    assert post["image_url"] == "https://img/deal.jpg"


@pytest.mark.asyncio
async def test_fallo_del_aviso_no_lanza_ni_marca_ni_envia_la_publicacion():
    deal = _deal()
    notifier, bot, _ = _notifier(deal, notice_ok=False)
    assert await notifier.notify([EVENT], NOW) == 0
    assert deal.admin_notified_at is None
    bot.send_preformatted.assert_not_called()


@pytest.mark.asyncio
async def test_excepcion_de_telegram_no_lanza():
    deal = _deal()
    notifier, bot, _ = _notifier(deal)
    bot.send_admin_notification.side_effect = RuntimeError("red caída")
    assert await notifier.notify([EVENT], NOW) == 0
    assert deal.admin_notified_at is None


@pytest.mark.asyncio
async def test_fallo_de_la_publicacion_mantiene_el_aviso_enviado():
    deal = _deal()
    notifier, _, _ = _notifier(deal, post_ok=False)
    assert await notifier.notify([EVENT], NOW) == 1
    assert deal.admin_notified_at == NOW


@pytest.mark.asyncio
async def test_con_cooldown_no_avisa_ni_dispara_alertas():
    deal = _deal(admin_notified_at=NOW - timedelta(days=2), admin_notified_price=Decimal("289.9"))
    notifier, bot, matcher = _notifier(deal)
    assert await notifier.notify([EVENT], NOW) == 0
    bot.send_admin_notification.assert_not_called()
    matcher.notify_matching_alerts.assert_not_awaited()


@pytest.mark.asyncio
async def test_sin_canal_configurado_solo_dispara_alertas():
    deal = _deal()
    notifier, bot, matcher = _notifier(deal, chat_id="")
    assert await notifier.notify([EVENT], NOW) == 0
    bot.send_admin_notification.assert_not_called()
    matcher.notify_matching_alerts.assert_awaited_once_with(deal)


@pytest.mark.asyncio
async def test_ignora_deals_borrados_o_no_activos():
    notifier, bot, _ = _notifier(None)
    assert await notifier.notify([EVENT], NOW) == 0
    notifier, bot, _ = _notifier(_deal(status="expired"))
    assert await notifier.notify([EVENT], NOW) == 0
    bot.send_admin_notification.assert_not_called()


@pytest.mark.asyncio
async def test_fallo_preparando_la_publicacion_no_corta_los_demas_avisos():
    first, second = _deal(id="d1", slug="uno"), _deal(id="d2", slug="dos")
    notifier, bot, _ = _notifier(first)
    notifier.deal_repo.get_by_id = AsyncMock(side_effect=lambda deal_id: {"d1": first, "d2": second}[deal_id])
    notifier.generator.generate_text = MagicMock(side_effect=[RuntimeError("plantilla"), "🍄 Dos"])

    sent = await notifier.notify(
        [OfferEvent("d1", "reactivated", Decimal("300")), OfferEvent("d2", "reactivated", Decimal("300"))], NOW
    )

    assert sent == 2
    assert first.admin_notified_at == NOW and second.admin_notified_at == NOW
    # solo la del segundo (publicación + versión WhatsApp); sin tarjeta, el post
    # lleva el precio aunque la plantilla no lo trajera
    texts = [call.kwargs["text"] for call in bot.send_preformatted.call_args_list]
    assert len(texts) == 2
    assert texts[0].startswith("🍄 Dos\n\n💶 Precio:") and texts[1].startswith("🔥 *Dos*")


# --- antigüedad mínima (10 días) ---


@pytest.mark.asyncio
async def test_publicado_en_telegram_hace_4_dias_no_avisa_al_admin_pero_si_alertas():
    deal = _deal()
    publication = SimpleNamespace(text="x", image_url=None, sent_at=NOW - timedelta(days=4))
    notifier, bot, matcher = _notifier(deal, publication=publication)

    assert await notifier.notify([OfferEvent("deal-1", "price_dropped", Decimal("320"))], NOW) == 0

    bot.send_admin_notification.assert_not_called()
    bot.send_preformatted.assert_not_called()
    matcher.notify_matching_alerts.assert_awaited_once_with(deal)
    assert deal.admin_notified_at is None


@pytest.mark.asyncio
async def test_publicado_en_telegram_hace_10_dias_si_avisa():
    publication = SimpleNamespace(text="no estándar", image_url=None, sent_at=NOW - timedelta(days=10))
    notifier, bot, _ = _notifier(_deal(), publication=publication)

    assert await notifier.notify([EVENT], NOW) == 1
    assert "hace 10 días" in bot.send_admin_notification.call_args.args[0]


@pytest.mark.asyncio
async def test_sin_telegram_cuenta_el_alta_en_la_web():
    notifier, bot, _ = _notifier(_deal(created_at=NOW - timedelta(days=3)), publication=None)
    assert await notifier.notify([EVENT], NOW) == 0
    bot.send_admin_notification.assert_not_called()


@pytest.mark.asyncio
async def test_fallo_leyendo_la_publicacion_usa_el_alta_en_la_web():
    notifier, bot, _ = _notifier(_deal())
    notifier.publications.latest_for_deal = AsyncMock(side_effect=RuntimeError("BD"))

    assert await notifier.notify([EVENT], NOW) == 1
    assert "nunca en Telegram" in bot.send_admin_notification.call_args.args[0]
