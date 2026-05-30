"""Tests unitarios para DealService.

No requieren BD ni red: el repositorio y AlertMatcher se mockean. Verifican
que la lógica de aplicación (autogenerar slug, asignar created_by según el
perfil, disparar notificaciones de alertas) se comporta como esperamos.

Se mockean también los modelos SQLAlchemy con SimpleNamespace para no
inicializar el mapper completo (que requeriría todos los módulos cargados).
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.modules.deals.application.deal_service import DealService


def _stub_deal(status: str = "active", **overrides):
    base = dict(
        id="11111111-1111-1111-1111-111111111111",
        title="Producto X",
        slug="producto-x",
        current_price=99.99,
        affiliate_url="https://example.com/p",
        status=status,
        created_by=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _build_service(*, has_profile: bool = True, with_matcher: bool = True):
    repo = MagicMock()
    repo.user_has_profile = AsyncMock(return_value=has_profile)
    # Capturamos el dict pasado a create() para inspeccionar lo construido por el servicio.
    # El servicio invoca Deal(**deal_data) — está patcheado a SimpleNamespace —
    # y pasa el resultado a repo.create. Devolvemos el mismo objeto con un id
    # asignado, simulando la persistencia.
    def _assign_id(deal_obj):
        deal_obj.id = "11111111-1111-1111-1111-111111111111"
        return deal_obj
    repo.create = AsyncMock(side_effect=_assign_id)
    repo.get_by_id = AsyncMock(side_effect=lambda _id: _stub_deal())
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    # Por defecto no hay duplicado de ASIN. Los tests que necesiten simular un
    # choque sobreescriben este AsyncMock devolviendo un stub de deal.
    repo.find_by_external_id = AsyncMock(return_value=None)

    matcher = None
    if with_matcher:
        matcher = MagicMock()
        matcher.notify_matching_alerts = AsyncMock(return_value=0)

    return DealService(repo, matcher), repo, matcher


@pytest.fixture(autouse=True)
def _patch_deal_constructor():
    """Sustituye `Deal(**deal_data)` por un SimpleNamespace equivalente. Así no
    necesitamos que el mapper SQLAlchemy esté completamente inicializado."""
    with patch("app.modules.deals.application.deal_service.Deal", side_effect=lambda **kw: SimpleNamespace(**kw)):
        yield


@pytest.mark.asyncio
async def test_create_deal_autogenera_slug_cuando_falta():
    service, repo, _ = _build_service()

    await service.create_deal({"title": "Mi Chollo Tope", "current_price": 10.0}, "user-1")

    created_deal = repo.create.call_args.args[0]
    assert created_deal.slug, "el slug no se ha generado"
    assert created_deal.slug.startswith("mi-chollo-tope")


@pytest.mark.asyncio
async def test_create_deal_asigna_created_by_cuando_el_perfil_existe():
    service, repo, _ = _build_service(has_profile=True)

    await service.create_deal({"title": "X", "current_price": 1.0}, "user-1")

    created = repo.create.call_args.args[0]
    assert created.created_by == "user-1"


@pytest.mark.asyncio
async def test_create_deal_omite_created_by_cuando_no_hay_perfil():
    service, repo, _ = _build_service(has_profile=False)

    await service.create_deal(
        {"title": "X", "current_price": 1.0, "created_by": "user-1"},
        "user-1",
    )

    created = repo.create.call_args.args[0]
    assert getattr(created, "created_by", None) is None


@pytest.mark.asyncio
async def test_create_deal_dispara_matcher_si_status_active():
    service, repo, matcher = _build_service()
    repo.get_by_id = AsyncMock(side_effect=lambda _id: _stub_deal(status="active"))

    await service.create_deal({"title": "X", "current_price": 1.0}, "user-1")

    matcher.notify_matching_alerts.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_deal_no_dispara_matcher_si_status_no_active():
    service, repo, matcher = _build_service()
    repo.get_by_id = AsyncMock(side_effect=lambda _id: _stub_deal(status="draft"))

    await service.create_deal({"title": "X", "current_price": 1.0}, "user-1")

    matcher.notify_matching_alerts.assert_not_called()


@pytest.mark.asyncio
async def test_update_deal_aplica_cambios_y_dispara_matcher():
    service, repo, matcher = _build_service()
    existing = _stub_deal(status="active", title="Antiguo")
    repo.get_by_id = AsyncMock(return_value=existing)

    result = await service.update_deal("id-x", {"title": "Nuevo título", "current_price": 79.0})

    assert existing.title == "Nuevo título"
    assert existing.current_price == 79.0
    matcher.notify_matching_alerts.assert_awaited_once()
    assert result is existing


@pytest.mark.asyncio
async def test_update_deal_devuelve_none_si_no_existe():
    service, repo, matcher = _build_service()
    repo.get_by_id = AsyncMock(return_value=None)

    result = await service.update_deal("id-x", {"title": "x"})

    assert result is None
    matcher.notify_matching_alerts.assert_not_called()


@pytest.mark.asyncio
async def test_create_deal_funciona_sin_matcher_inyectado():
    service, repo, _ = _build_service(with_matcher=False)

    deal = await service.create_deal({"title": "X", "current_price": 1.0}, "user-1")

    assert deal is not None  # no explota aunque matcher sea None


# ── Deduplicación por external_id (ASIN) ─────────────────────────────────────

from app.modules.deals.domain.exceptions import DuplicateDealError  # noqa: E402


@pytest.mark.asyncio
async def test_create_deal_falla_si_external_id_ya_existe():
    service, repo, _ = _build_service()
    repo.find_by_external_id = AsyncMock(
        return_value=_stub_deal(id="otro-id", slug="producto-x", title="Producto X")
    )

    with pytest.raises(DuplicateDealError) as exc_info:
        await service.create_deal(
            {"title": "Nuevo", "current_price": 9.99, "external_id": "B0DABC1234"},
            "user-1",
        )

    repo.create.assert_not_called()
    assert exc_info.value.http_status == 409
    payload = exc_info.value.payload
    assert payload["code"] == "DUPLICATE_DEAL"
    assert payload["existing_deal"] == {
        "id": "otro-id",
        "slug": "producto-x",
        "title": "Producto X",
    }


@pytest.mark.asyncio
async def test_create_deal_ok_con_external_id_unico():
    service, repo, _ = _build_service()
    # find_by_external_id devuelve None por defecto en _build_service.

    await service.create_deal(
        {"title": "Nuevo", "current_price": 9.99, "external_id": "B0DABC1234"},
        "user-1",
    )

    repo.find_by_external_id.assert_awaited_once_with("B0DABC1234", exclude_id=None)
    repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_update_deal_falla_si_external_id_choca_con_otro():
    service, repo, _ = _build_service()
    repo.get_by_id = AsyncMock(return_value=_stub_deal(id="propio-id"))
    repo.find_by_external_id = AsyncMock(
        return_value=_stub_deal(id="otro-id", slug="producto-x", title="Producto X")
    )

    with pytest.raises(DuplicateDealError):
        await service.update_deal("propio-id", {"external_id": "B0NEW00000"})

    repo.update.assert_not_called()
    repo.find_by_external_id.assert_awaited_once_with(
        "B0NEW00000", exclude_id="propio-id"
    )


@pytest.mark.asyncio
async def test_update_deal_ok_si_external_id_no_viene_en_el_payload():
    """Si el PUT no toca external_id, no se valida nada (evita query inútil)."""
    service, repo, _ = _build_service()
    repo.get_by_id = AsyncMock(return_value=_stub_deal(id="propio-id"))

    await service.update_deal("propio-id", {"title": "Sólo cambio el título"})

    repo.find_by_external_id.assert_not_called()
    repo.update.assert_awaited_once()
