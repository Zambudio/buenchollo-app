"""Tests de la integración con Sentry.

Cubre:
- Sin `SENTRY_DSN`, `init_sentry()` no llama a sentry_sdk.init y devuelve False.
- Con DSN, sí inicializa y propaga environment/release/sample_rate.
- El hook `_before_send` añade el `request_id` del contextvar como tag.
- `before_send` sin request_id no rompe.
- Si `sentry_sdk.init` lanza excepción, `init_sentry` la captura y devuelve False.
"""
from unittest.mock import patch
import pytest

from app.core.config import Settings
from app.core.request_id import _request_id_ctx
from app.core.sentry import _before_send, init_sentry


# ── init_sentry ────────────────────────────────────────────────────────────

def test_init_sentry_sin_dsn_no_inicializa_nada():
    settings = Settings(sentry_dsn="")

    with patch("app.core.sentry.sentry_sdk.init") as mock_init:
        result = init_sentry(settings)

    assert result is False
    mock_init.assert_not_called()


def test_init_sentry_con_dsn_inicializa_y_propaga_config():
    settings = Settings(
        sentry_dsn="https://abc@sentry.io/12345",
        sentry_environment="production",
        sentry_release="v1.2.3",
        sentry_traces_sample_rate=0.1,
    )

    with patch("app.core.sentry.sentry_sdk.init") as mock_init:
        result = init_sentry(settings)

    assert result is True
    mock_init.assert_called_once()
    kwargs = mock_init.call_args.kwargs
    assert kwargs["dsn"] == "https://abc@sentry.io/12345"
    assert kwargs["environment"] == "production"
    assert kwargs["release"] == "v1.2.3"
    assert kwargs["traces_sample_rate"] == 0.1
    assert kwargs["send_default_pii"] is False


def test_init_sentry_usa_app_env_si_sentry_environment_vacio():
    settings = Settings(
        sentry_dsn="https://abc@sentry.io/12345",
        sentry_environment="",
        app_env="staging",
    )

    with patch("app.core.sentry.sentry_sdk.init") as mock_init:
        init_sentry(settings)

    assert mock_init.call_args.kwargs["environment"] == "staging"


def test_init_sentry_captura_excepciones_y_no_propaga():
    settings = Settings(sentry_dsn="https://abc@sentry.io/12345")

    with patch("app.core.sentry.sentry_sdk.init", side_effect=RuntimeError("boom")):
        result = init_sentry(settings)

    assert result is False


# ── _before_send ───────────────────────────────────────────────────────────

def test_before_send_anade_request_id_si_hay_uno_en_contexto():
    token = _request_id_ctx.set("abc123hex")
    try:
        event: dict = {}
        result = _before_send(event, {})

        assert result is event
        assert event["tags"]["request_id"] == "abc123hex"
    finally:
        _request_id_ctx.reset(token)


def test_before_send_sin_request_id_no_rompe_y_no_anade_tag():
    # Aseguramos contexto limpio
    token = _request_id_ctx.set(None)
    try:
        event: dict = {}
        result = _before_send(event, {})

        assert result is event
        assert "tags" not in event or "request_id" not in event.get("tags", {})
    finally:
        _request_id_ctx.reset(token)


def test_before_send_preserva_tags_existentes():
    token = _request_id_ctx.set("rid-1")
    try:
        event = {"tags": {"feature": "comments"}}
        _before_send(event, {})

        assert event["tags"]["feature"] == "comments"  # no se pisa
        assert event["tags"]["request_id"] == "rid-1"
    finally:
        _request_id_ctx.reset(token)
