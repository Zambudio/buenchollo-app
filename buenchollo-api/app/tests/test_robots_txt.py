"""Tests de /robots.txt.

Cubre:
- `/robots.txt` responde 200 en texto plano y bloquea todo rastreo
  (`Disallow: /` para todos los user-agents).
- La ruta no aparece en el schema OpenAPI (es infraestructura, no contrato).
"""
from fastapi.testclient import TestClient

from app.main import app


def test_robots_txt_bloquea_todo_rastreo():
    client = TestClient(app)

    r = client.get("/robots.txt")

    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert "User-agent: *" in r.text
    assert "Disallow: /" in r.text


def test_robots_txt_no_aparece_en_openapi():
    client = TestClient(app)

    schema = client.get("/openapi.json").json()

    assert "/robots.txt" not in schema["paths"]
