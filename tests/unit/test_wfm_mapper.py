from datetime import UTC, datetime

import pytest

from app.application.wfm_mapper import to_market_item, to_order
from app.config import settings
from app.domain.order import OrderType
from tests.support import load_data, merged_raw_items

ASSETS = settings.WF_MARKET_ASSETS_URL


@pytest.fixture
def items_by_slug():
    return {item.slug: item for item in map(to_market_item, merged_raw_items())}


class TestToMarketItem:
    def test_maps_all_fixture_items_with_three_languages(self, items_by_slug):
        assert items_by_slug
        for item in items_by_slug.values():
            assert item.names.en
            assert item.names.zh_hant
            assert item.names.zh_hans
            assert item.image is not None

    def test_maps_fields(self, items_by_slug):
        item = items_by_slug["primed_continuity"]

        assert item.id == "54c6855ee779891362942572"
        assert item.names.en == "Primed Continuity"
        assert item.names.zh_hans == "持久力 Prime"
        assert item.max_rank == 10
        assert "mod" in item.tags
        assert isinstance(item.tags, tuple)
        assert item.game_ref.startswith("/Lotus/")

    def test_image_paths_become_full_urls(self, items_by_slug):
        item = items_by_slug["primed_continuity"]

        assert item.thumb.startswith(f"{ASSETS}items/images/")
        assert item.icon.startswith(f"{ASSETS}items/images/")
        assert item.sub_icon is None

    def test_empty_thumb_falls_back_to_icon(self, items_by_slug):
        item = items_by_slug["vadarya_prime_blueprint"]

        assert item.thumb is None
        assert item.image == f"{ASSETS}items/unknown.png"
        assert item.sub_icon == f"{ASSETS}sub_icons/blueprint_128x128.png"

    def test_single_language_leaves_other_chinese_empty(self):
        raw = load_data("items_zh-hant.json")[0]
        item = to_market_item(raw)

        assert item.names.zh_hant
        assert item.names.zh_hans is None

    def test_missing_english_name_falls_back_to_slug(self):
        item = to_market_item({"id": "x", "slug": "mystery_item", "i18n": {}})

        assert item.names.en == "mystery_item"
        assert item.image is None

    @pytest.mark.parametrize(
        "base_url", ["https://cdn.example/assets", "https://cdn.example/assets/"]
    )
    def test_custom_assets_url_joins_with_single_slash(self, base_url):
        raw = {
            "id": "x",
            "slug": "x",
            "i18n": {"en": {"name": "X", "icon": "/items/x.png"}},
        }
        item = to_market_item(raw, assets_base_url=base_url)

        assert item.icon == "https://cdn.example/assets/items/x.png"


class TestToOrder:
    def test_maps_all_user_orders(self):
        orders = [to_order(raw) for raw in load_data("user_orders.json")]

        assert len(orders) == 17
        assert all(o.type is OrderType.BUY for o in orders)

    def test_maps_fields(self):
        raw = load_data("user_orders.json")[0]
        order = to_order(raw)

        assert order.id == raw["id"]
        assert order.item_id == raw["itemId"]
        assert order.platinum == raw["platinum"]
        assert order.quantity == raw["quantity"]
        assert order.per_trade == raw["perTrade"]
        assert order.visible == raw["visible"]

    def test_parses_timestamps_as_utc(self):
        order = to_order(
            {
                "id": "o",
                "type": "buy",
                "itemId": "i",
                "platinum": 5,
                "quantity": 1,
                "createdAt": "2026-09-21T14:42:38Z",
            }
        )

        assert order.created_at == datetime(2026, 9, 21, 14, 42, 38, tzinfo=UTC)
        assert order.updated_at is None

    def test_rank_is_optional(self):
        raws = load_data("user_orders.json")
        with_rank = next(r for r in raws if "rank" in r)
        without_rank = next(r for r in raws if "rank" not in r)

        assert to_order(with_rank).rank == with_rank["rank"]
        assert to_order(without_rank).rank is None

    def test_maps_top_orders_ignoring_user_info(self):
        top = load_data("top_orders_primed_continuity.json")
        sell = [to_order(raw) for raw in top["sell"]]
        buy = [to_order(raw) for raw in top["buy"]]

        assert sell
        assert buy
        assert all(o.type is OrderType.SELL for o in sell)
        assert all(o.type is OrderType.BUY for o in buy)

    def test_unknown_type_raises(self):
        raw = load_data("user_orders.json")[0] | {"type": "trade"}
        with pytest.raises(ValueError):
            to_order(raw)
