from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.modules.deals.api.schemas import DealCardResponse, DealCreate, DealDetailResponse
from app.modules.deals.application.deal_service import DealService
from app.modules.deals.domain.models import Deal
from app.modules.users.domain.models import Profile


def _deal(**overrides) -> Deal:
    data = dict(
        id="11111111-1111-1111-1111-111111111111",
        title="Chollo",
        slug="chollo",
        current_price=10.0,
        temperature=0,
        status="active",
        source="manual",
        affiliate_url="https://example.com/x",
        images=[],
        votes_up=0,
        votes_down=0,
        click_count=0,
        comment_count=0,
        favorite_count=0,
        show_keepa_chart=False,
    )
    data.update(overrides)
    return Deal(**data)


def _profile() -> Profile:
    return Profile(username="pepe", display_name="Pepe", avatar_url=None)


def test_card_exposes_author_only_for_community():
    community = _deal(source="community", author=_profile())
    assert DealCardResponse.model_validate(community).author.username == "pepe"

    manual = _deal(source="manual", author=_profile())
    assert DealCardResponse.model_validate(manual).author is None


def test_detail_exposes_coupon_code():
    deal = _deal(coupon_code="AHORRA10", status="active")
    assert DealDetailResponse.model_validate(deal).coupon_code == "AHORRA10"


def test_deal_create_rejects_coupon_over_64():
    base = dict(title="t", current_price=1, affiliate_url="https://example.com")
    with pytest.raises(ValidationError):
        DealCreate(**base, coupon_code="x" * 65)
    assert DealCreate(**base, coupon_code="x" * 64).coupon_code == "x" * 64


@pytest.mark.asyncio
async def test_create_deal_sets_canonical_url():
    repo = MagicMock()
    repo.find_by_external_id = AsyncMock(return_value=None)
    repo.user_has_profile = AsyncMock(return_value=False)
    repo.create = AsyncMock(side_effect=lambda d: d)
    repo.get_by_id = AsyncMock(side_effect=lambda _id: created["deal"])
    created = {}

    async def create(d):
        d.id = "22222222-2222-2222-2222-222222222222"
        created["deal"] = d
        return d

    repo.create = create
    service = DealService(repo)
    deal = await service.create_deal(
        {
            "title": "Chollo",
            "current_price": 10,
            "affiliate_url": "https://www.amazon.es/dp/B0ABCDEFGH?tag=x",
            "external_id": "B0ABCDEFGH",
        },
        "user-1",
    )
    assert deal.canonical_url == "https://www.amazon.es/dp/B0ABCDEFGH"


@pytest.mark.asyncio
async def test_update_deal_recomputes_canonical_and_tolerates_invalid():
    deal = _deal(affiliate_url="https://www.amazon.es/dp/B0ABCDEFGH", external_id="B0ABCDEFGH")
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=deal)
    repo.find_by_external_id = AsyncMock(return_value=None)
    repo.update = AsyncMock()
    service = DealService(repo)
    await service.update_deal("id", {"affiliate_url": "https://www.amazon.es/dp/B0ZZZZZZZZ?tag=a", "external_id": "B0ZZZZZZZZ"})
    assert deal.canonical_url == "https://www.amazon.es/dp/B0ZZZZZZZZ"
    await service.update_deal("id", {"affiliate_url": "sin enlace"})
    assert deal.canonical_url is None
