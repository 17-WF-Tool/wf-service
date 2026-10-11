from dataclasses import FrozenInstanceError

import pytest

from app.domain.market_item import ItemNames, MarketItem
from app.domain.order import Order, OrderType


def make_item(**overrides) -> MarketItem:
    fields = {
        "id": "item-1",
        "slug": "primed_continuity",
        "names": ItemNames(en="Primed Continuity", zh_hant="持久力 Prime"),
        "tags": ("mod", "legendary"),
    }
    return MarketItem(**(fields | overrides))


def make_order(**overrides) -> Order:
    fields = {
        "id": "order-1",
        "type": OrderType.SELL,
        "item_id": "item-1",
        "platinum": 50,
        "quantity": 2,
    }
    return Order(**(fields | overrides))


class TestItemNames:
    @pytest.mark.parametrize("language", ["zh-hant", "zh_hant", "ZH-HANT"])
    def test_get_accepts_language_formats(self, language):
        names = ItemNames(en="Primed Continuity", zh_hant="持久力 Prime")
        assert names.get(language) == "持久力 Prime"

    @pytest.mark.parametrize("language", ["zh-hans", "ja", ""])
    def test_get_falls_back_to_english(self, language):
        names = ItemNames(en="Primed Continuity", zh_hant="持久力 Prime")
        assert names.get(language) == "Primed Continuity"


class TestMarketItem:
    def test_image_prefers_thumb(self):
        item = make_item(thumb="thumb.webp", icon="icon.webp")
        assert item.image == "thumb.webp"

    def test_image_falls_back_to_icon(self):
        item = make_item(thumb=None, icon="icon.webp")
        assert item.image == "icon.webp"

    def test_image_is_none_without_any_image(self):
        assert make_item().image is None

    def test_has_tag(self):
        item = make_item()
        assert item.has_tag("mod")
        assert not item.has_tag("weapon")

    def test_is_immutable(self):
        item = make_item()
        with pytest.raises(FrozenInstanceError):
            item.slug = "changed"


class TestOrder:
    def test_order_type_compares_with_string(self):
        assert OrderType.BUY == "buy"
        assert OrderType("sell") is OrderType.SELL

    def test_update_price(self):
        order = make_order()
        order.update_price(1)
        assert order.platinum == 1

    @pytest.mark.parametrize("platinum", [0, -1])
    def test_update_price_rejects_below_one(self, platinum):
        order = make_order()
        with pytest.raises(ValueError, match="至少為 1 白金"):
            order.update_price(platinum)
        assert order.platinum == 50

    def test_update_quantity(self):
        order = make_order()
        order.update_quantity(5)
        assert order.quantity == 5

    @pytest.mark.parametrize("quantity", [0, -3])
    def test_update_quantity_rejects_below_one(self, quantity):
        order = make_order()
        with pytest.raises(ValueError, match="數量至少為 1"):
            order.update_quantity(quantity)
        assert order.quantity == 2

    def test_set_visibility(self):
        order = make_order()
        order.set_visibility(False)
        assert order.visible is False
