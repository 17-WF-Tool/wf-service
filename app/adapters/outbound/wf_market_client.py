import logging
from typing import Any
from urllib.parse import quote, urlencode

from curl_cffi.requests import AsyncSession, RequestsError

from app.adapters.outbound.rate_limiter import RateLimiter
from app.ports.market_client_port import MarketClientPort

logger = logging.getLogger(__name__)


class WarframeMarketClient(MarketClientPort):
    def __init__(
        self,
        base_url: str = "https://api.warframe.market/v2",
        platform: str = "pc",
        timeout: float = 15,
        min_request_interval: float = 0.35,
    ):
        self.base_url = base_url.rstrip("/")
        self.platform = platform
        self.timeout = timeout
        # 官方限制約每秒 3 個請求，所有請求共用同一個限制器
        self._rate_limiter = RateLimiter(min_request_interval)

    async def fetch_versions(self) -> dict[str, Any]:
        return await self._get("/versions")

    async def fetch_items(self, language: str = "zh-hant") -> list[dict[str, Any]]:
        return await self._get("/items", language=language)

    async def fetch_user_orders(self, username: str) -> list[dict[str, Any]]:
        clean_username = username.strip()
        try:
            return await self._get(f"/orders/user/{_encode(clean_username)}")
        except KeyError as e:
            raise KeyError(f"找不到 Warframe.market 使用者: {clean_username}") from e

    async def fetch_top_orders(
        self, slug: str, rank: int | None = None
    ) -> dict[str, list[dict[str, Any]]]:
        clean_slug = slug.strip()
        params = {"rank": rank} if rank is not None else None
        try:
            data = await self._get(
                f"/orders/item/{_encode(clean_slug)}/top", params=params
            )
        except KeyError as e:
            raise KeyError(f"找不到 Warframe.market 物品: {clean_slug}") from e
        return {"sell": data.get("sell", []), "buy": data.get("buy", [])}

    async def _get(
        self,
        path: str,
        language: str = "en",
        params: dict[str, Any] | None = None,
    ) -> Any:
        """發送 GET 請求並取出官方回應外殼 {apiVersion, data, error} 中的 data"""
        url = f"{self.base_url}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"
        headers = {
            "accept": "application/json",
            "language": language,
            "platform": self.platform,
            "crossplay": "true",
        }

        await self._rate_limiter.wait()
        try:
            # 模擬 Chrome TLS 指紋，避免遭 Cloudflare 阻擋
            async with AsyncSession(impersonate="chrome124") as session:
                response = await session.get(url, headers=headers, timeout=self.timeout)
        except RequestsError as e:
            raise RuntimeError(f"Market API 連線失敗: {e}") from e

        logger.info("[Market API] GET %s | 狀態碼: %s", url, response.status_code)

        if response.status_code == 404:
            raise KeyError(f"Market API 找不到資源: {path}")
        if response.status_code != 200:
            raise RuntimeError(f"Market API 回應失敗: HTTP {response.status_code}")

        try:
            payload = response.json()
        except ValueError as e:
            raise RuntimeError("Market API 回應不是有效的 JSON") from e

        if payload.get("error"):
            raise RuntimeError(f"Market API 回傳錯誤: {payload['error']}")
        return payload.get("data")


def _encode(segment: str) -> str:
    """將路徑片段完整編碼，包含 /，避免使用者輸入改變請求路徑"""
    return quote(segment, safe="")
