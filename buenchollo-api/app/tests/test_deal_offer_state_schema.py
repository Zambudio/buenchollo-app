"""El detalle público expone el estado de la oferta del catálogo permanente."""
from datetime import datetime, timezone
from types import SimpleNamespace

from app.modules.deals.api.schemas import DealDetailResponse


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
