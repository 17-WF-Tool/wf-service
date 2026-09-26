from abc import ABC, abstractmethod

from app.domain.item import Item


class ItemRepositoryPort(ABC):
    @abstractmethod
    async def get_by_category(self, category: str) -> list[Item]:
        """依類別取得物品列表"""

    @abstractmethod
    async def get_by_id(self, item_id: str) -> Item | None:
        """依 ID 取得單一物品"""

    @abstractmethod
    async def save(self, item: Item) -> None:
        """儲存物品狀態"""
