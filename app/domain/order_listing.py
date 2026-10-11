from dataclasses import dataclass

from app.domain.market_item import MarketItem
from app.domain.order import Order


@dataclass(frozen=True)
class OrderListing:
    """掛單與其物品資訊；物品目錄查不到時 item 為 None"""

    order: Order
    item: MarketItem | None = None
