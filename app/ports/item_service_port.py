from abc import ABC, abstractmethod

from app.domain.item import Item
from app.domain.order import OrderType
from app.domain.order_listing import OrderListing


class ItemServicePort(ABC):
    @abstractmethod
    async def list_items_by_category(self, category: str) -> list[Item]:
        pass

    @abstractmethod
    async def update_item_price(self, item_id: str, new_price: int) -> Item:
        pass

    @abstractmethod
    async def toggle_item_visibility(self, item_id: str, is_visible: bool) -> Item:
        pass

    @abstractmethod
    async def get_user_orders(
        self,
        username: str | None = None,
        order_type: OrderType | None = None,
    ) -> list[OrderListing]:
        """取得使用者的公開掛單並附上物品資訊；未指定 order_type 時回傳全部"""
