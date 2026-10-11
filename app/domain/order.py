from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class OrderType(StrEnum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    """Warframe.market 的單筆掛單，欄位語意對應官方 v2 order"""

    id: str
    type: OrderType
    item_id: str
    platinum: int
    quantity: int
    per_trade: int = 1
    rank: int | None = None
    subtype: str | None = None
    visible: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def update_price(self, platinum: int) -> None:
        if platinum < 1:
            raise ValueError("價格至少為 1 白金")
        self.platinum = platinum

    def update_quantity(self, quantity: int) -> None:
        if quantity < 1:
            raise ValueError("數量至少為 1")
        self.quantity = quantity

    def set_visibility(self, visible: bool) -> None:
        self.visible = visible
