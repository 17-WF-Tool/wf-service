import pytest

from tests.support import FakeMarketClient, load_data

ORDERS_URL = "/api/v1/market/me/orders"
USER_ORDERS_URL = "/api/v1/market/users/{username}/orders"
VORUNA_SYSTEMS_ID = "69d67675b3984cc97e241750"


def test_health_check(api_client, make_service):
    client = api_client(make_service())

    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_returns_orders_in_envelope(api_client, make_service):
    client = api_client(make_service())

    response = client.get(ORDERS_URL, params={"username": "someone"})

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["message"] == "success"
    assert len(body["data"]) == 17


def test_order_includes_item_info(api_client, make_service):
    raw = load_data("user_orders.json")[0]
    client = api_client(make_service(FakeMarketClient(user_orders=[raw])))

    response = client.get(ORDERS_URL, params={"username": "someone"})

    [order] = response.json()["data"]
    assert order["id"] == raw["id"]
    assert order["type"] == "buy"
    assert order["platinum"] == raw["platinum"]
    assert order["per_trade"] == raw["perTrade"]
    assert order["visible"] == raw["visible"]
    item = order["item"]
    assert item["id"] == VORUNA_SYSTEMS_ID
    assert item["slug"] == "voruna_prime_systems_blueprint"
    assert item["names"] == {
        "en": "Voruna Prime Systems Blueprint",
        "zh_hant": "Voruna Prime 系統 藍圖",
        "zh_hans": "Voruna Prime 系统 蓝图",
    }
    assert item["image"].endswith(".webp")
    assert "blueprint" in item["tags"]


def test_unknown_item_returns_only_id(api_client, make_service):
    raw = load_data("user_orders.json")[0] | {"itemId": "unknown-item"}
    client = api_client(make_service(FakeMarketClient(user_orders=[raw])))

    response = client.get(ORDERS_URL, params={"username": "someone"})

    assert response.status_code == 200
    [order] = response.json()["data"]
    assert order["item"] == {
        "id": "unknown-item",
        "slug": None,
        "names": None,
        "image": None,
        "tags": [],
    }


@pytest.mark.parametrize(("order_type", "expected"), [("buy", 17), ("sell", 1)])
def test_filters_by_type(api_client, make_service, order_type, expected):
    raw = load_data("user_orders.json")
    raw.append(raw[0] | {"id": "sell-order", "type": "sell"})
    client = api_client(make_service(FakeMarketClient(user_orders=raw)))

    response = client.get(
        ORDERS_URL, params={"username": "someone", "type": order_type}
    )

    data = response.json()["data"]
    assert len(data) == expected
    assert {order["type"] for order in data} == {order_type}


def test_invalid_type_returns_422(api_client, make_service):
    client = api_client(make_service())

    response = client.get(ORDERS_URL, params={"username": "someone", "type": "x"})

    assert response.status_code == 422


def test_users_route_uses_path_username(api_client, make_service):
    fake = FakeMarketClient()
    client = api_client(make_service(fake, default_username="default_user"))

    response = client.get(
        USER_ORDERS_URL.format(username="path_user"), params={"type": "buy"}
    )

    assert response.status_code == 200
    assert len(response.json()["data"]) == 17
    assert fake.calls == [("fetch_user_orders", ("path_user",))]


def test_missing_username_returns_400(api_client, make_service):
    client = api_client(make_service(default_username=""))

    response = client.get(ORDERS_URL)

    assert response.status_code == 400


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (KeyError("找不到 Warframe.market 使用者: ghost"), 404),
        (RuntimeError("Market API 回應失敗: HTTP 503"), 502),
        (OSError("network down"), 502),
        (Exception("unexpected"), 500),
    ],
)
def test_maps_errors_to_status_codes(api_client, make_service, error, status_code):
    fake = FakeMarketClient(errors={"fetch_user_orders": error})
    client = api_client(make_service(fake))

    response = client.get(ORDERS_URL, params={"username": "ghost"})

    assert response.status_code == status_code


def test_unknown_user_message_has_no_quotes(api_client, make_service):
    error = KeyError("找不到 Warframe.market 使用者: ghost")
    fake = FakeMarketClient(errors={"fetch_user_orders": error})
    client = api_client(make_service(fake))

    response = client.get(ORDERS_URL, params={"username": "ghost"})

    assert response.json()["detail"] == "找不到 Warframe.market 使用者: ghost"
