from datetime import datetime, timezone
from types import SimpleNamespace
import pytest
from pydantic import ValidationError

from app.modules.scheduled_deals.api.schemas import ScheduledDealCreate, ScheduledDealResponse
from app.modules.scheduled_deals.domain.models import ScheduledDealStatus


def test_short_title_is_allowed_but_blank_title_is_rejected():
    payload = {
        "title": "TV", "offer_price": 0, "affiliate_url": "",
        "category_id": None, "scheduled_at": datetime.now(timezone.utc),
    }
    assert ScheduledDealCreate.model_validate(payload).title == "TV"
    with pytest.raises(ValidationError):
        ScheduledDealCreate.model_validate({**payload, "title": "  "})


def test_scheduled_deal_response_exposes_all_editable_web_fields():
    now = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)
    linked_deal = SimpleNamespace(
        short_description="Resumen web",
        images=["https://example.com/one.jpg", "https://example.com/two.jpg"],
        store_id="store-id",
        subcategory_id="subcategory-id",
        brand="Marca",
        shipping_info="Envío gratis",
        expires_at=datetime(2026, 9, 30, 20, 0, tzinfo=timezone.utc),
        show_keepa_chart=True,
    )
    scheduled = SimpleNamespace(
        id="scheduled-id",
        deal_id="deal-id",
        asin="B0H7X5D6QN",
        web_ready=True,
        title="Producto",
        description_web="Descripción web",
        telegram_text="Texto Telegram",
        telegram_channel_id=None,
        offer_price=99.99,
        regular_price=129.99,
        discount_percentage=23,
        image_url="https://example.com/main.jpg",
        affiliate_url="https://link.amazon/example",
        store_name="Amazon",
        category_id="category-id",
        scheduled_at=datetime(2026, 9, 27, 11, 0, tzinfo=timezone.utc),
        expires_at=linked_deal.expires_at,
        status=ScheduledDealStatus.SCHEDULED,
        cancellation_reason=None,
        created_at=now,
        updated_at=now,
        deal=linked_deal,
    )

    response = ScheduledDealResponse.model_validate(scheduled).model_dump()

    expected_web_fields = {
        "short_description": "Resumen web",
        "images": ["https://example.com/one.jpg", "https://example.com/two.jpg"],
        "store_id": "store-id",
        "subcategory_id": "subcategory-id",
        "brand": "Marca",
        "shipping_info": "Envío gratis",
        "show_keepa_chart": True,
    }
    assert {key: response.get(key) for key in expected_web_fields} == expected_web_fields

    scheduled.asin = None
    scheduled.category_id = None
    scheduled.web_ready = False
    pending_response = ScheduledDealResponse.model_validate(scheduled)
    assert pending_response.asin is None
    assert pending_response.category_id is None
    assert pending_response.web_ready is False
