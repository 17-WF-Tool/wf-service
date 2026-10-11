from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PriceQuote:
    """單一報價；rank 為該掛單的 Mod 等級，不分等級的物品為 None"""

    platinum: int
    rank: int | None = None


@dataclass(frozen=True)
class ItemPrice:
    """物品市價，取自線上使用者的最低賣單與最高收購單

    rank 為查詢條件；未指定時兩邊報價可能是不同等級。
    """

    slug: str
    rank: int | None
    lowest_sell: PriceQuote | None
    highest_buy: PriceQuote | None
    updated_at: datetime
