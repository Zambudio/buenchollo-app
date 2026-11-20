from unittest.mock import MagicMock

from app.modules.telegram.application.whatsapp_copy import send_whatsapp_copy


def _bot(*results):
    bot = MagicMock()
    bot.send_preformatted = MagicMock(side_effect=list(results))
    return bot


def test_envia_la_version_whatsapp_en_texto_plano_con_la_imagen():
    bot = _bot(True)

    assert send_whatsapp_copy(bot, chat_id="-100admin", telegram_text="🍄 Monitor", image_url="https://img/x.jpg")

    bot.send_preformatted.assert_called_once_with(
        text="🔥 *Monitor*", entities=[], image_url="https://img/x.jpg", chat_id="-100admin"
    )


def test_usa_el_texto_editado_en_el_panel():
    bot = _bot(True)

    send_whatsapp_copy(bot, chat_id="-100admin", telegram_text="🍄 Monitor", whatsapp_text="Mi versión")

    assert bot.send_preformatted.call_args.kwargs["text"] == "Mi versión"


def test_si_falla_la_foto_reintenta_solo_con_texto():
    bot = _bot(False, True)

    assert send_whatsapp_copy(bot, chat_id="-100admin", telegram_text="🍄 Monitor", image_url="https://img/x.jpg")

    assert bot.send_preformatted.call_args.kwargs["image_url"] is None


def test_nunca_lanza_y_sin_canal_admin_no_envia():
    bot = _bot(RuntimeError("red"))
    assert send_whatsapp_copy(bot, chat_id="-100admin", telegram_text="🍄 Monitor") is False

    bot = _bot()
    assert send_whatsapp_copy(bot, chat_id="", telegram_text="🍄 Monitor") is False
    bot.send_preformatted.assert_not_called()
