import json
from typing import Any

import pytest
from curl_cffi.requests import RequestsError

from app.adapters.outbound import wf_market_client
from app.adapters.outbound.wf_market_client import WarframeMarketClient
from tests.support import load_fixture

BASE_URL = "https://api.example/v2"


class FakeResponse:
    def __init__(self, status_code: int, body: Any):
        self.status_code = status_code
        self._text = body if isinstance(body, str) else json.dumps(body)

    def json(self) -> Any:
        return json.loads(self._text)


class FakeSession:
    """取代 curl_cffi 的 AsyncSession，記錄請求並回傳預設回應"""

    def __init__(self, response: FakeResponse | None, error: Exception | None):
        self.response = response
        self.error = error
        self.requests: list[dict[str, Any]] = []
        self.impersonate: str | None = None

    def __call__(self, impersonate: str | None = None):
        self.impersonate = impersonate
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def get(self, url: str, headers: dict[str, str], timeout: float):
        self.requests.append({"url": url, "headers": headers, "timeout": timeout})
        if self.error:
            raise self.error
        return self.response


@pytest.fixture
def respond(monkeypatch):
    """設定假回應：respond(status, body) 或 respond(error=例外)"""

    def _respond(
        status_code: int = 200, body: Any = None, error: Exception | None = None
    ) -> FakeSession:
        session = FakeSession(FakeResponse(status_code, body), error)
        monkeypatch.setattr(wf_market_client, "AsyncSession", session)
        return session

    return _respond


@pytest.fixture
def client() -> WarframeMarketClient:
    return WarframeMarketClient(base_url=f"{BASE_URL}/", platform="pc", timeout=5)


class TestRequest:
    async def test_sends_expected_headers_and_impersonation(self, respond, client):
        session = respond(200, load_fixture("versions.json"))

        await client.fetch_versions()

        request = session.requests[0]
        assert request["url"] == f"{BASE_URL}/versions"
        assert request["timeout"] == 5
        assert request["headers"]["platform"] == "pc"
        assert request["headers"]["crossplay"] == "true"
        assert request["headers"]["language"] == "en"
        assert session.impersonate == "chrome124"

    async def test_fetch_items_passes_language(self, respond, client):
        session = respond(200, load_fixture("items_zh-hans.json"))

        items = await client.fetch_items("zh-hans")

        assert session.requests[0]["url"] == f"{BASE_URL}/items"
        assert session.requests[0]["headers"]["language"] == "zh-hans"
        assert "zh-hans" in items[0]["i18n"]

    @pytest.mark.parametrize(
        ("username", "expected_path"),
        [
            ("  someone  ", "/orders/user/someone"),
            ("a b/../c?x", "/orders/user/a%20b%2F..%2Fc%3Fx"),
        ],
    )
    async def test_username_is_stripped_and_encoded(
        self, respond, client, username, expected_path
    ):
        session = respond(200, load_fixture("user_orders.json"))

        await client.fetch_user_orders(username)

        assert session.requests[0]["url"] == f"{BASE_URL}{expected_path}"


class TestResponse:
    async def test_returns_data_without_envelope(self, respond, client):
        respond(200, load_fixture("versions.json"))

        versions = await client.fetch_versions()

        assert "collections" in versions
        assert "apiVersion" not in versions

    async def test_user_orders_are_not_filtered_by_type(self, respond, client):
        envelope = load_fixture("user_orders.json")
        sell = envelope["data"][0] | {"id": "sell-order", "type": "sell"}
        envelope["data"].append(sell)
        respond(200, envelope)

        orders = await client.fetch_user_orders("someone")

        assert {o["type"] for o in orders} == {"buy", "sell"}
        assert len(orders) == len(envelope["data"])

    async def test_top_orders_returns_both_sides(self, respond, client):
        respond(200, load_fixture("top_orders_primed_continuity.json"))

        top = await client.fetch_top_orders("primed_continuity")

        assert top["sell"]
        assert top["buy"]

    async def test_top_orders_fills_missing_side(self, respond, client):
        respond(200, {"apiVersion": "0", "data": {"sell": []}, "error": None})

        top = await client.fetch_top_orders("primed_continuity")

        assert top == {"sell": [], "buy": []}


class TestErrors:
    async def test_unknown_user_raises_key_error(self, respond, client):
        respond(404, load_fixture("error_user_not_found.json"))

        with pytest.raises(KeyError, match="找不到 Warframe.market 使用者: ghost"):
            await client.fetch_user_orders(" ghost ")

    async def test_unknown_item_raises_key_error(self, respond, client):
        respond(404, {"apiVersion": "0", "data": None, "error": {"request": []}})

        with pytest.raises(KeyError, match="找不到 Warframe.market 物品: nope"):
            await client.fetch_top_orders("nope")

    @pytest.mark.parametrize("status_code", [400, 429, 500, 503])
    async def test_non_200_raises_runtime_error(self, respond, client, status_code):
        respond(status_code, {"error": "x"})

        with pytest.raises(RuntimeError, match=f"HTTP {status_code}"):
            await client.fetch_versions()

    async def test_invalid_json_raises_runtime_error(self, respond, client):
        respond(200, "<html>Cloudflare challenge</html>")

        with pytest.raises(RuntimeError, match="不是有效的 JSON"):
            await client.fetch_versions()

    async def test_error_field_raises_runtime_error(self, respond, client):
        respond(200, {"apiVersion": "0", "data": None, "error": {"request": ["x"]}})

        with pytest.raises(RuntimeError, match="回傳錯誤"):
            await client.fetch_versions()

    async def test_connection_error_raises_runtime_error(self, respond, client):
        respond(error=RequestsError("Could not resolve host"))

        with pytest.raises(RuntimeError, match="連線失敗"):
            await client.fetch_versions()
