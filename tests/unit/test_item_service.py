import logging

import pytest

from app.application.catalog_service import CatalogService
from app.domain.order import OrderType
from tests.support import FakeMarketClient, load_data

VORUNA_SYSTEMS_ID = "69d67675b3984cc97e241750"


def with_sell_order(orders: list[dict]) -> list[dict]:
    sell = orders[0] | {"id": "sell-order", "type": "sell"}
    return [*orders, sell]


class TestGetUserOrders:
    async def test_returns_buy_and_sell_orders(self, make_service):
        raw = with_sell_order(load_data("user_orders.json"))
        service = make_service(FakeMarketClient(user_orders=raw))

        listings = await service.get_user_orders("someone")

        assert len(listings) == len(raw)
        assert {listing.order.type for listing in listings} == {
            OrderType.BUY,
            OrderType.SELL,
        }

    async def test_buy_only_account_returns_orders(self, make_service):
        raw = load_data("user_orders.json")
        assert {o["type"] for o in raw} == {"buy"}
        service = make_service(FakeMarketClient(user_orders=raw))

        listings = await service.get_user_orders("someone")

        assert len(listings) == len(raw)

    async def test_maps_order_fields(self, make_service):
        raw = load_data("user_orders.json")[0]
        service = make_service(FakeMarketClient(user_orders=[raw]))

        [listing] = await service.get_user_orders("someone")

        assert listing.order.id == raw["id"]
        assert listing.order.item_id == raw["itemId"]
        assert listing.order.platinum == raw["platinum"]
        assert listing.order.quantity == raw["quantity"]
        assert listing.order.visible == raw["visible"]

    async def test_attaches_item_from_catalog(self, make_service):
        raw = load_data("user_orders.json")[0]
        service = make_service(FakeMarketClient(user_orders=[raw]))

        [listing] = await service.get_user_orders("someone")

        assert listing.item.id == VORUNA_SYSTEMS_ID
        assert listing.item.slug == "voruna_prime_systems_blueprint"
        assert listing.item.names.en == "Voruna Prime Systems Blueprint"
        assert listing.item.names.zh_hant == "Voruna Prime 系統 藍圖"
        assert listing.item.image.startswith("https://warframe.market/static/assets/")

    async def test_every_fixture_order_has_item(self, make_service):
        service = make_service()

        listings = await service.get_user_orders("someone")

        assert all(listing.item is not None for listing in listings)

    async def test_unknown_item_returns_order_without_item(self, make_service):
        raw = load_data("user_orders.json")[0] | {"itemId": "unknown-item"}
        service = make_service(FakeMarketClient(user_orders=[raw]))

        [listing] = await service.get_user_orders("someone")

        assert listing.order.item_id == "unknown-item"
        assert listing.item is None

    async def test_catalog_failure_does_not_fail_request(self, make_service):
        raw = load_data("user_orders.json")[0]
        broken = FakeMarketClient(errors={"fetch_versions": RuntimeError("down")})
        service = make_service(
            FakeMarketClient(user_orders=[raw]), catalog=CatalogService(broken)
        )

        [listing] = await service.get_user_orders("someone")

        assert listing.item is None

    @pytest.mark.parametrize("order_type", [OrderType.BUY, OrderType.SELL])
    async def test_filters_by_order_type(self, make_service, order_type):
        raw = with_sell_order(load_data("user_orders.json"))
        service = make_service(FakeMarketClient(user_orders=raw))

        listings = await service.get_user_orders("someone", order_type)

        expected = sum(1 for o in raw if o["type"] == order_type)
        assert len(listings) == expected
        assert all(listing.order.type == order_type for listing in listings)

    async def test_skips_malformed_orders(self, make_service, caplog):
        raw = [*load_data("user_orders.json"), {"id": "broken"}]
        service = make_service(FakeMarketClient(user_orders=raw))

        with caplog.at_level(logging.WARNING):
            listings = await service.get_user_orders("someone")

        assert len(listings) == len(raw) - 1
        assert "broken" in caplog.text

    async def test_uses_given_username(self, make_service):
        client = FakeMarketClient()
        service = make_service(client, default_username="default_user")

        await service.get_user_orders("given_user")

        assert client.calls == [("fetch_user_orders", ("given_user",))]

    async def test_falls_back_to_default_username(self, make_service):
        client = FakeMarketClient()
        service = make_service(client, default_username="default_user")

        await service.get_user_orders()

        assert client.calls == [("fetch_user_orders", ("default_user",))]

    async def test_without_any_username_raises_value_error(self, make_service):
        client = FakeMarketClient()
        service = make_service(client)

        with pytest.raises(ValueError, match="未指定使用者名稱"):
            await service.get_user_orders()
        assert client.calls == []

    async def test_propagates_unknown_user(self, make_service):
        client = FakeMarketClient(errors={"fetch_user_orders": KeyError("ghost")})
        service = make_service(client)

        with pytest.raises(KeyError):
            await service.get_user_orders("ghost")
