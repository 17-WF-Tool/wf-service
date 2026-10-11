from abc import ABC, abstractmethod

from app.domain.item_price import ItemPrice


class PriceServicePort(ABC):
    @abstractmethod
    async def get_item_price(self, slug: str, rank: int | None = None) -> ItemPrice:
        """取得物品市價；找不到物品丟 KeyError，官方通訊失敗丟 RuntimeError"""
