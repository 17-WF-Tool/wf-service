from abc import ABC, abstractmethod
from typing import Any


class MarketClientPort(ABC):
    """Warframe.market v2 官方 API 的存取介面

    實作只負責取得資料，回傳官方 `data` 欄位的原始內容，不做業務過濾。
    錯誤約定：找不到資源丟 KeyError，其他通訊失敗丟 RuntimeError。
    """

    @abstractmethod
    async def fetch_versions(self) -> dict[str, Any]:
        """取得各資料集版本資訊（含 collections.items）"""

    @abstractmethod
    async def fetch_items(self, language: str = "zh-hant") -> list[dict[str, Any]]:
        """取得完整物品目錄，i18n 會包含 en 與指定語言"""

    @abstractmethod
    async def fetch_user_orders(self, username: str) -> list[dict[str, Any]]:
        """公開查詢特定使用者的所有掛單（買單與賣單）"""

    @abstractmethod
    async def fetch_top_orders(
        self, slug: str, rank: int | None = None
    ) -> dict[str, list[dict[str, Any]]]:
        """取得特定物品線上使用者的最低賣單與最高買單

        格式為 {"sell": [...], "buy": [...]}；rank 可篩選 Mod 等級，
        不給時兩邊可能是不同等級的掛單。
        """
