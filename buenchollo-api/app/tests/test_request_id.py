"""Tests del middleware RequestId y la inyección en logs.

Cubre:
- Generación automática de UUID4 hex.
- Respeto al `X-Request-Id` entrante (proxy / load balancer).
- Header `X-Request-Id` siempre presente en la respuesta.
- `get_request_id()` accesible desde el endpoint que sirve la petición.
- Filtro de logging que añade `record.request_id` con el valor del contexto.
"""
import logging
import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.logging import _JsonFormatter, _RequestIdFilter
from app.core.request_id import (
    REQUEST_ID_HEADER,
    RequestIdMiddleware,
    get_request_id,
)


@pytest.fixture
def client_with_middleware() -> TestClient:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/echo")
    def echo() -> dict:
        return {"rid": get_request_id() or ""}

    return TestClient(app)


def test_genera_request_id_si_no_viene_en_la_peticion(client_with_middleware):
    r = client_with_middleware.get("/echo")

    rid = r.headers.get(REQUEST_ID_HEADER)
    assert rid is not None
    assert re.fullmatch(r"[0-9a-f]{32}", rid), "UUID4 hex de 32 chars"
    assert r.json() == {"rid": rid}


def test_respeta_request_id_entrante(client_with_middleware):
    incoming = "trace-from-nginx-abc-123"
    r = client_with_middleware.get("/echo", headers={REQUEST_ID_HEADER: incoming})

    assert r.headers[REQUEST_ID_HEADER] == incoming
    assert r.json() == {"rid": incoming}


def test_request_id_distinto_por_peticion(client_with_middleware):
    r1 = client_with_middleware.get("/echo")
    r2 = client_with_middleware.get("/echo")

    assert r1.headers[REQUEST_ID_HEADER] != r2.headers[REQUEST_ID_HEADER]


def test_filter_inyecta_request_id_en_logrecord():
    f = _RequestIdFilter()
    record = logging.LogRecord("x", logging.INFO, "x.py", 1, "msg", (), None)
    assert f.filter(record) is True
    assert record.request_id == "-"  # fuera de petición devuelve "-"


def test_json_formatter_incluye_campos_extra():
    formatter = _JsonFormatter()
    record = logging.LogRecord(
        "test.logger", logging.WARNING, "x.py", 1, "ha pasado %s", ("algo",), None
    )
    record.request_id = "abc123"
    record.user_id = "u-1"  # campo extra
    record.payload = {"k": "v"}

    line = formatter.format(record)

    import json as _json

    data = _json.loads(line)
    assert data["level"] == "WARNING"
    assert data["logger"] == "test.logger"
    assert data["msg"] == "ha pasado algo"
    assert data["request_id"] == "abc123"
    assert data["user_id"] == "u-1"
    assert data["payload"] == {"k": "v"}
    assert "ts" in data
