from datetime import datetime, timezone
from types import SimpleNamespace

from app.modules.scheduled_deals.api.schemas import ScheduledDealResponse
from app.modules.scheduled_deals.domain.models import ScheduledDealStatus


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
