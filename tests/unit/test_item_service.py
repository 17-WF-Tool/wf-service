import pytest

from tests.support import FakeMarketClient, load_data


def with_sell_order(orders: list[dict]) -> list[dict]:
    sell = orders[0] | {"id": "sell-order", "type": "sell"}
    return [*orders, sell]


class TestGetMyPublicOrders:
    async def test_returns_buy_and_sell_orders(self, make_service):
        raw = with_sell_order(load_data("user_orders.json"))
        service = make_service(FakeMarketClient(user_orders=raw))

        orders = await service.get_my_public_orders("someone")

        assert len(orders) == len(raw)
        assert {o["order_type"] for o in orders} == {"buy", "sell"}

    async def test_formats_order_fields(self, make_service):
        raw = load_data("user_orders.json")[0]
        service = make_service(FakeMarketClient(user_orders=[raw]))

        [order] = await service.get_my_public_orders("someone")

        assert order["order_id"] == raw["id"]
        assert order["platinum"] == raw["platinum"]
        assert order["quantity"] == raw["quantity"]
        assert order["is_visible"] == raw["visible"]

    async def test_uses_given_username(self, make_service):
        client = FakeMarketClient()
        service = make_service(client, default_username="default_user")

        await service.get_my_public_orders("given_user")

        assert client.calls == [("fetch_user_orders", ("given_user",))]

    async def test_falls_back_to_default_username(self, make_service):
        client = FakeMarketClient()
        service = make_service(client, default_username="default_user")

        await service.get_my_public_orders()

        assert client.calls == [("fetch_user_orders", ("default_user",))]

    async def test_without_any_username_raises_value_error(self, make_service):
        client = FakeMarketClient()
        service = make_service(client)

        with pytest.raises(ValueError, match="未指定使用者名稱"):
            await service.get_my_public_orders()
        assert client.calls == []

    async def test_propagates_unknown_user(self, make_service):
        client = FakeMarketClient(errors={"fetch_user_orders": KeyError("ghost")})
        service = make_service(client)

        with pytest.raises(KeyError):
            await service.get_my_public_orders("ghost")
