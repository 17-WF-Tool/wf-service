from abc import ABC, abstractmethod
from typing import Any

from app.domain.item import Item


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
    async def get_my_public_orders(
        self, username: str | None = None
    ) -> list[dict[str, Any]]:
        pass
