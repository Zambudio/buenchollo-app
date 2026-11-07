"""Seguridad del cliente de Telegram: el token no se filtra y la descarga de
imágenes no puede apuntar a la red interna (SSRF)."""
import logging
from unittest.mock import MagicMock, patch

import requests

from app.modules.telegram.infrastructure import telegram_bot as tb
from app.modules.telegram.infrastructure.telegram_bot import TelegramBot

TOKEN = "123456:SECRET-TOKEN-ABC"


def _connection_error() -> requests.ConnectionError:
    return requests.ConnectionError(
        f"HTTPSConnectionPool(host='api.telegram.org', port=443): "
        f"Max retries exceeded with url: /bot{TOKEN}/sendMessage"
    )


def test_error_de_conexion_no_expone_el_token(caplog):
    bot = TelegramBot(TOKEN, default_chat_id="@canal")
    with patch.object(tb.requests, "post", side_effect=_connection_error()), caplog.at_level(logging.DEBUG):
        assert bot.send_preformatted("hola", entities=[]) is False

    assert TOKEN not in (bot.last_error or "")
    assert "<token>" in (bot.last_error or "")
    assert TOKEN not in caplog.text


def test_aviso_admin_fallido_no_expone_el_token(caplog):
    bot = TelegramBot(TOKEN, default_chat_id="@admin")
    with patch.object(tb.requests, "post", side_effect=_connection_error()), caplog.at_level(logging.DEBUG):
        assert bot.send_admin_notification("aviso") is False

    assert TOKEN not in caplog.text


def test_descarga_de_imagen_rechaza_ip_interna():
    with patch.object(tb.requests, "get") as get:
        assert TelegramBot._download_image("http://192.168.1.10/foto.jpg") is None
        get.assert_not_called()


def test_descarga_de_imagen_rechaza_esquemas_no_http():
    with patch.object(tb.requests, "get") as get:
        assert TelegramBot._download_image("file:///etc/passwd") is None
        get.assert_not_called()


def _response(*, status=200, headers=None, chunks=(b"img",), redirect=False):
    resp = MagicMock()
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = None
    resp.ok = 200 <= status < 400
    resp.is_redirect = redirect
    resp.headers = headers or {"content-type": "image/png"}
    resp.iter_content.return_value = iter(chunks)
    return resp


def test_redireccion_a_ip_interna_se_bloquea_antes_de_seguirla():
    redirect = _response(status=302, redirect=True, headers={"location": "http://10.0.0.5/secreto"})
    with (
        patch.object(tb, "resolves_to_private_ip", side_effect=lambda url: "10.0.0.5" in url),
        patch.object(tb.requests, "get", return_value=redirect) as get,
    ):
        assert TelegramBot._download_image("https://cdn.example.com/foto.png") is None
    assert get.call_count == 1


def test_imagen_demasiado_grande_se_descarta():
    big = _response(chunks=[b"x" * (tb.MAX_IMAGE_BYTES // 2 + 1)] * 2)
    with (
        patch.object(tb, "resolves_to_private_ip", return_value=False),
        patch.object(tb.requests, "get", return_value=big),
    ):
        assert TelegramBot._download_image("https://cdn.example.com/foto.png") is None


def test_imagen_valida_se_descarga():
    ok = _response(chunks=[b"abc", b"def"], headers={"content-type": "image/webp; q=1"})
    with (
        patch.object(tb, "resolves_to_private_ip", return_value=False),
        patch.object(tb.requests, "get", return_value=ok),
    ):
        assert TelegramBot._download_image("https://cdn.example.com/foto.webp") == (b"abcdef", "image/webp")
