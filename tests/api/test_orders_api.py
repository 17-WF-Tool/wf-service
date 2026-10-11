import pytest

from tests.support import FakeMarketClient

ORDERS_URL = "/api/v1/market/me/orders"


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
