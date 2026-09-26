from abc import ABC, abstractmethod
from typing import Any


class MarketClientPort(ABC):
    @abstractmethod
    async def fetch_lowest_price(self, name_en: str) -> int | None:
        """向外部 Warframe.market 取得最低賣單價格"""

    @abstractmethod
    async def fetch_user_public_orders(self, username: str) -> list[dict[str, Any]]:
        """公開查詢特定使用者的掛單列表"""
