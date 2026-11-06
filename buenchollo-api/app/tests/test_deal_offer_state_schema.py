"""El detalle público expone el estado de la oferta del catálogo permanente."""
from datetime import datetime, timezone
from types import SimpleNamespace

from app.modules.deals.api.schemas import DealCardResponse, DealDetailResponse


def test_detalle_incluye_motivo_de_fin_y_ultima_comprobacion():
    checked = datetime(2026, 11, 5, 4, 0, tzinfo=timezone.utc)
    deal = SimpleNamespace(
        id="d1", title="X", slug="x", current_price=10, previous_price=None, discount_percentage=None,
        savings_amount=None, image_url=None, images=[], affiliate_url="https://a", source_url=None,
        store=None, category=None, subcategory=None, temperature=0, comment_count=0, published_at=checked,
        status="expired", source="manual", brand=None, public_author=None,
        offer_end_reason="price_increase", last_price_check_at=checked,
    )
    body = DealDetailResponse.model_validate(deal).model_dump()
    assert body["offer_end_reason"] == "price_increase"
    assert body["last_price_check_at"] == checked


def test_tarjeta_y_detalle_exponen_el_producto_vinculado():
    checked = datetime(2026, 11, 5, 4, 0, tzinfo=timezone.utc)
    deal = SimpleNamespace(
        id="d1", product_id="53d83eb6-166f-4d79-a7bc-9aa8e7aa61ec", title="Monitor", slug="monitor",
        current_price=100, previous_price=None, discount_percentage=None, savings_amount=None,
        image_url=None, images=[], affiliate_url="https://a", source_url=None, store=None, category=None,
        subcategory=None, temperature=0, comment_count=0, published_at=checked, status="published",
        source="manual", brand=None, public_author=None, offer_end_reason=None, last_price_check_at=None,
    )
    assert DealCardResponse.model_validate(deal).product_id == deal.product_id
    assert DealDetailResponse.model_validate(deal).product_id == deal.product_id
