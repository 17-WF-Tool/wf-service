from typing import Any

from curl_cffi.requests import AsyncSession

from app.ports.market_client_port import MarketClientPort


class WarframeMarketClient(MarketClientPort):
    def __init__(self, base_url: str = "https://api.warframe.market/v2"):
        self.base_url = base_url

    async def fetch_lowest_price(self, name_en: str) -> int | None:
        return None

    async def fetch_user_public_orders(self, username: str) -> list[dict[str, Any]]:
        clean_username = username.strip()
        url = f"{self.base_url}/orders/user/{clean_username}"

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "language": "en",
            "platform": "pc",
            "origin": "https://warframe.market",
            "referer": f"https://warframe.market/profile/{clean_username}",
        }

        async with AsyncSession(impersonate="chrome124") as session:
            response = await session.get(url, headers=headers, timeout=10)

            print(f"[Market API] 請求路徑: {url} | 狀態碼: {response.status_code}")

            if response.status_code == 404:
                raise KeyError(f"找不到 Warframe.market 使用者: {clean_username}")
            if response.status_code != 200:
                raise RuntimeError(f"Market API 回應失敗: HTTP {response.status_code}")

            res_json = response.json()
            orders_list = res_json.get("data", [])

            # 過濾出賣單
            sell_orders = [
                order for order in orders_list if order.get("type") == "sell"
            ]
            return sell_orders
