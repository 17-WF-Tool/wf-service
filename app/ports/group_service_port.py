from abc import ABC, abstractmethod

from app.domain.item_group import ItemGroup
from app.domain.market_item import MarketItem


class GroupServicePort(ABC):
    @abstractmethod
    def list_groups(self) -> list[ItemGroup]:
        """取得所有分組"""

    @abstractmethod
    def get_group_items(self, group_id: str) -> list[MarketItem]:
        """取得分組內存在於物品目錄的物品；找不到分組丟 KeyError"""
