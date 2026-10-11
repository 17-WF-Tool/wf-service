from abc import ABC, abstractmethod

from app.domain.order import OrderType
from app.domain.order_listing import OrderListing


class OrderServicePort(ABC):
    @abstractmethod
    async def get_user_orders(
        self,
        username: str | None = None,
        order_type: OrderType | None = None,
    ) -> list[OrderListing]:
        """取得使用者的公開掛單並附上物品資訊；未指定 order_type 時回傳全部"""
