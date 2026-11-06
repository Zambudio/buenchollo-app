"""Telegram apagado de verdad en local y en tests.

Antes: local-env ponía TELEGRAM_*='' (en PowerShell eso BORRA la variable) y
Settings leía el `.env` real, así que el entorno local y los tests de
integración enviaban avisos reales al canal Admin.
"""
from app.core.config import Settings


def test_telegram_desactivado_vacia_token_y_canales():
    settings = Settings(
        telegram_enabled=False,
        telegram_bot_token="real-token",
        telegram_main_channel_id="-100main",
        telegram_admin_channel_id="-100admin",
    )
    assert settings.telegram_bot_token == ""
    assert settings.telegram_main_channel_id == ""
    assert settings.telegram_admin_channel_id == ""


def test_telegram_activo_por_defecto_conserva_la_configuracion():
    settings = Settings(telegram_enabled=True, telegram_bot_token="t", telegram_admin_channel_id="a")
    assert settings.telegram_bot_token == "t" and settings.telegram_admin_channel_id == "a"


def test_la_suite_corre_con_telegram_apagado():
    """conftest.py exporta TELEGRAM_ENABLED=false antes de cargar la app."""
    assert Settings().telegram_enabled is False
    assert Settings().telegram_admin_channel_id == ""
