import asyncio
from datetime import UTC, datetime

import pytest

from app.application.price_service import PriceService
from app.domain.item_price import PriceQuote
from tests.support import FakeMarketClient, load_data

FIXED_NOW = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def make_price_service(clock):
    def _make(client: FakeMarketClient | None = None, **kwargs) -> PriceService:
        options = {"cache_ttl": 300, "clock": clock, "now": lambda: FIXED_NOW}
        return PriceService(client or FakeMarketClient(), **(options | kwargs))

    return _make


def top_orders(sell: list[tuple[int, int | None]], buy: list[tuple[int, int | None]]):
    """以 (白金, 等級) 組出官方 top 回應"""
    template = load_data("top_orders_primed_continuity.json")["sell"][0]

    def make(side: str, platinum: int, rank: int | None, index: int) -> dict:
        return template | {
            "id": f"{side}-{index}",
            "type": side,
            "platinum": platinum,
            "rank": rank,
        }

    return {
        "sell": [make("sell", p, r, i) for i, (p, r) in enumerate(sell)],
        "buy": [make("buy", p, r, i) for i, (p, r) in enumerate(buy)],
    }


class TestGetItemPrice:
    async def test_returns_lowest_sell_and_highest_buy(self, make_price_service):
        top = top_orders(sell=[(50, 0), (45, 0), (48, 0)], buy=[(30, 0), (35, 0)])
        service = make_price_service(FakeMarketClient(top_orders=top))

        price = await service.get_item_price("primed_continuity")

        assert price.slug == "primed_continuity"
        assert price.rank is None
        assert price.lowest_sell == PriceQuote(platinum=45, rank=0)
        assert price.highest_buy == PriceQuote(platinum=35, rank=0)
        assert price.updated_at == FIXED_NOW

    async def test_from_recorded_fixture(self, make_price_service):
        service = make_price_service()

        price = await service.get_item_price("primed_continuity")

        assert price.lowest_sell == PriceQuote(platinum=45, rank=0)
        assert price.highest_buy == PriceQuote(platinum=71, rank=10)

    async def test_passes_rank_to_client(self, make_price_service, fake_client):
        service = make_price_service(fake_client)

        price = await service.get_item_price("primed_continuity", rank=10)

        assert price.rank == 10
        assert fake_client.calls == [("fetch_top_orders", ("primed_continuity", 10))]

    async def test_empty_side_is_none(self, make_price_service):
        top = top_orders(sell=[(20, None)], buy=[])
        service = make_price_service(FakeMarketClient(top_orders=top))

        price = await service.get_item_price("some_item")

        assert price.lowest_sell == PriceQuote(platinum=20, rank=None)
        assert price.highest_buy is None

    async def test_skips_malformed_orders(self, make_price_service):
        top = top_orders(sell=[(40, 0)], buy=[(30, 0)])
        top["sell"].append({"id": "broken"})
        service = make_price_service(FakeMarketClient(top_orders=top))

        price = await service.get_item_price("primed_continuity")

        assert price.lowest_sell.platinum == 40

    async def test_normalizes_slug(self, make_price_service, fake_client):
        service = make_price_service(fake_client)

        price = await service.get_item_price("  Primed_Continuity ")

        assert price.slug == "primed_continuity"
        assert fake_client.calls[0][1][0] == "primed_continuity"

    async def test_propagates_errors_and_does_not_cache(
        self, make_price_service, fake_client
    ):
        fake_client.errors["fetch_top_orders"] = KeyError("找不到 Warframe.market 物品")
        service = make_price_service(fake_client)

        with pytest.raises(KeyError):
            await service.get_item_price("nope")
        del fake_client.errors["fetch_top_orders"]
        await service.get_item_price("nope")

        assert fake_client.call_count("fetch_top_orders") == 2


class TestCache:
    async def test_repeated_query_within_ttl_uses_cache(
        self, make_price_service, fake_client, clock
    ):
        service = make_price_service(fake_client)

        first = await service.get_item_price("primed_continuity")
        clock.advance(299)
        second = await service.get_item_price("primed_continuity")

        assert second is first
        assert fake_client.call_count("fetch_top_orders") == 1

    async def test_expired_cache_fetches_again(
        self, make_price_service, fake_client, clock
    ):
        service = make_price_service(fake_client)

        await service.get_item_price("primed_continuity")
        clock.advance(300)
        await service.get_item_price("primed_continuity")

        assert fake_client.call_count("fetch_top_orders") == 2

    async def test_cache_is_per_slug_and_rank(self, make_price_service, fake_client):
        service = make_price_service(fake_client)

        await service.get_item_price("primed_continuity")
        await service.get_item_price("primed_continuity", rank=10)
        await service.get_item_price("primed_continuity", rank=10)
        await service.get_item_price("other_item")

        assert fake_client.call_count("fetch_top_orders") == 3

    async def test_concurrent_queries_fetch_once(self, make_price_service, fake_client):
        service = make_price_service(fake_client)

        results = await asyncio.gather(
            *(service.get_item_price("primed_continuity") for _ in range(5))
        )

        assert fake_client.call_count("fetch_top_orders") == 1
        assert all(result is results[0] for result in results)
        assert service._locks == {}

    async def test_expired_entries_are_pruned(
        self, make_price_service, fake_client, clock
    ):
        service = make_price_service(fake_client)

        await service.get_item_price("item_a")
        clock.advance(300)
        await service.get_item_price("item_b")

        assert list(service._cache) == [("item_b", None)]
