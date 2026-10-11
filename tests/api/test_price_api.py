from datetime import UTC, datetime

import pytest

from app.application.price_service import PriceService
from tests.support import FakeMarketClient

PRICE_URL = "/api/v1/market/items/{slug}/price"


def make_price_service(client: FakeMarketClient | None = None) -> PriceService:
    return PriceService(
        client or FakeMarketClient(),
        now=lambda: datetime(2026, 10, 11, 12, 0, tzinfo=UTC),
    )


def test_returns_price_in_envelope(api_client):
    client = api_client(price_service=make_price_service())

    response = client.get(PRICE_URL.format(slug="primed_continuity"))

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"] == {
        "slug": "primed_continuity",
        "rank": None,
        "lowest_sell": {"platinum": 45, "rank": 0},
        "highest_buy": {"platinum": 71, "rank": 10},
        "updated_at": "2026-10-11T12:00:00Z",
    }


def test_passes_rank(api_client):
    fake = FakeMarketClient()
    client = api_client(price_service=make_price_service(fake))

    response = client.get(
        PRICE_URL.format(slug="primed_continuity"), params={"rank": 10}
    )

    assert response.json()["data"]["rank"] == 10
    assert fake.calls == [("fetch_top_orders", ("primed_continuity", 10))]


def test_repeated_query_hits_official_once(api_client):
    fake = FakeMarketClient()
    client = api_client(price_service=make_price_service(fake))

    for _ in range(3):
        client.get(PRICE_URL.format(slug="primed_continuity"))

    assert fake.call_count("fetch_top_orders") == 1


@pytest.mark.parametrize("rank", ["-1", "abc"])
def test_invalid_rank_returns_422(api_client, rank):
    client = api_client(price_service=make_price_service())

    response = client.get(
        PRICE_URL.format(slug="primed_continuity"), params={"rank": rank}
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (KeyError("找不到 Warframe.market 物品: nope"), 404),
        (RuntimeError("Market API 回應失敗: HTTP 503"), 502),
        (OSError("network down"), 502),
    ],
)
def test_maps_errors_to_status_codes(api_client, error, status_code):
    fake = FakeMarketClient(errors={"fetch_top_orders": error})
    client = api_client(price_service=make_price_service(fake))

    response = client.get(PRICE_URL.format(slug="nope"))

    assert response.status_code == status_code


def test_unknown_item_message_has_no_quotes(api_client):
    fake = FakeMarketClient(
        errors={"fetch_top_orders": KeyError("找不到 Warframe.market 物品: nope")}
    )
    client = api_client(price_service=make_price_service(fake))

    response = client.get(PRICE_URL.format(slug="nope"))

    assert response.json()["detail"] == "找不到 Warframe.market 物品: nope"
