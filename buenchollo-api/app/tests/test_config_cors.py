"""Tests del parseo de CORS_ORIGINS en Settings.

La variable de entorno debe aceptar tanto CSV plano como JSON array (el
formato histórico de los .env desplegados), sin dejar corchetes ni
comillas en los orígenes resultantes.
"""
from app.core.config import Settings


def _origins(value: str) -> list[str]:
    return Settings(cors_origins=value).cors_origins


def test_csv_plano():
    assert _origins("https://a.com,https://b.com") == ["https://a.com", "https://b.com"]


def test_json_array():
    assert _origins('["https://a.com","https://b.com"]') == ["https://a.com", "https://b.com"]


def test_json_array_con_espacios():
    assert _origins('[ "https://a.com" , "https://b.com" ]') == ["https://a.com", "https://b.com"]


def test_valor_unico_sin_comas():
    assert _origins("https://a.com") == ["https://a.com"]


def test_asterisco():
    assert _origins("*") == ["*"]


def test_cadena_vacia_da_lista_vacia():
    assert _origins("") == []


def test_json_invalido_cae_a_csv():
    # Un valor que empieza por "[" pero no es JSON no debe reventar el arranque.
    assert _origins("[oops,https://a.com") == ["[oops", "https://a.com"]
