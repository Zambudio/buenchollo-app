"""Tests de la jerarquía de excepciones de dominio y su mapeo HTTP.

Verifica:
- Que el `http_status` declarado en cada subtipo es el esperado.
- Que el `domain_exception_handler` de `main.py` las traduce a JSONResponse
  con el status correcto cuando se lanzan desde un endpoint.
"""
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import (
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from app.modules.alerts.domain.exceptions import AlertNotFound
from app.modules.categories.domain.exceptions import CategoryNotFound
from app.modules.comments.domain.exceptions import (
    CommentNotFound,
    InvalidParentComment,
    InvalidVote,
    NotCommentOwner,
)
from app.modules.deals.domain.exceptions import DealNotFound
from app.modules.stores.domain.exceptions import StoreNotFound
from app.modules.users.domain.exceptions import ProfileNotFound


def test_http_status_por_subtipo():
    assert NotFoundError().http_status == 404
    assert ForbiddenError().http_status == 403
    assert ConflictError().http_status == 409
    assert ValidationError().http_status == 400
    assert ServiceUnavailableError().http_status == 503


def test_excepciones_de_modulo_heredan_status():
    assert DealNotFound("x").http_status == 404
    assert AlertNotFound().http_status == 404
    assert CategoryNotFound().http_status == 404
    assert StoreNotFound().http_status == 404
    assert ProfileNotFound().http_status == 404
    assert CommentNotFound().http_status == 404
    assert NotCommentOwner().http_status == 403
    assert InvalidParentComment().http_status == 400
    assert InvalidVote().http_status == 400


def test_mensaje_es_legible():
    assert "Deal" in str(DealNotFound("abc"))
    assert "abc" in str(DealNotFound("abc"))
    assert str(AlertNotFound()) == "Alerta no encontrada"
    assert str(CommentNotFound()) == "Comentario no encontrado"
    assert str(NotCommentOwner()) == "No puedes modificar este comentario"


def test_handler_global_traduce_a_json_response():
    """Levanta una app mínima con el handler y comprueba que la respuesta
    tiene el status code y el body esperados."""
    from app.main import domain_exception_handler

    app = FastAPI()
    app.add_exception_handler(DomainError, domain_exception_handler)

    router = APIRouter()

    @router.get("/raise-404")
    def _raise_404():
        raise DealNotFound("test-id")

    @router.get("/raise-403")
    def _raise_403():
        raise NotCommentOwner()

    @router.get("/raise-400")
    def _raise_400():
        raise InvalidVote()

    @router.get("/raise-503")
    def _raise_503():
        raise ServiceUnavailableError("Amazon caído")

    app.include_router(router)
    client = TestClient(app)

    r = client.get("/raise-404")
    assert r.status_code == 404
    assert r.json() == {"detail": "Deal 'test-id' no encontrado"}

    r = client.get("/raise-403")
    assert r.status_code == 403
    assert r.json() == {"detail": "No puedes modificar este comentario"}

    r = client.get("/raise-400")
    assert r.status_code == 400
    assert r.json() == {"detail": "Voto inválido (debe ser 1 o -1)"}

    r = client.get("/raise-503")
    assert r.status_code == 503
    assert r.json() == {"detail": "Amazon caído"}
