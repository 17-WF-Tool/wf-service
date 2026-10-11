from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from app.domain.item_group import ItemGroup
from app.domain.item_price import ItemPrice, PriceQuote
from app.domain.market_item import ItemNames, MarketItem
from app.domain.order import OrderType
from app.domain.order_listing import OrderListing

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: T | None = None


class ItemNamesDTO(BaseModel):
    en: str
    zh_hant: str | None = None
    zh_hans: str | None = None

    @classmethod
    def from_domain(cls, names: ItemNames) -> "ItemNamesDTO":
        return cls(en=names.en, zh_hant=names.zh_hant, zh_hans=names.zh_hans)


class MarketItemDTO(BaseModel):
    id: str
    slug: str
    names: ItemNamesDTO
    image: str | None = None
    tags: list[str] = Field(default_factory=list)
    max_rank: int | None = None

    @classmethod
    def from_domain(cls, item: MarketItem) -> "MarketItemDTO":
        return cls(
            id=item.id,
            slug=item.slug,
            names=ItemNamesDTO.from_domain(item.names),
            image=item.image,
            tags=list(item.tags),
            max_rank=item.max_rank,
        )


class ItemGroupDTO(BaseModel):
    id: str
    names: ItemNamesDTO
    item_count: int

    @classmethod
    def from_domain(cls, group: ItemGroup) -> "ItemGroupDTO":
        return cls(
            id=group.id,
            names=ItemNamesDTO.from_domain(group.names),
            item_count=len(group.slugs),
        )


class OrderItemDTO(BaseModel):
    """掛單的物品資訊；物品目錄查不到時只有 id"""

    id: str
    slug: str | None = None
    names: ItemNamesDTO | None = None
    image: str | None = None
    tags: list[str] = Field(default_factory=list)

    @classmethod
    def from_domain(cls, item_id: str, item: MarketItem | None) -> "OrderItemDTO":
        if item is None:
            return cls(id=item_id)
        return cls(
            id=item.id,
            slug=item.slug,
            names=ItemNamesDTO.from_domain(item.names),
            image=item.image,
            tags=list(item.tags),
        )


class UserOrderDTO(BaseModel):
    id: str
    type: OrderType
    platinum: int
    quantity: int
    per_trade: int
    rank: int | None = None
    subtype: str | None = None
    visible: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    item: OrderItemDTO

    @classmethod
    def from_domain(cls, listing: OrderListing) -> "UserOrderDTO":
        order = listing.order
        return cls(
            id=order.id,
            type=order.type,
            platinum=order.platinum,
            quantity=order.quantity,
            per_trade=order.per_trade,
            rank=order.rank,
            subtype=order.subtype,
            visible=order.visible,
            created_at=order.created_at,
            updated_at=order.updated_at,
            item=OrderItemDTO.from_domain(order.item_id, listing.item),
        )


class PriceQuoteDTO(BaseModel):
    platinum: int
    rank: int | None = None

    @classmethod
    def from_domain(cls, quote: PriceQuote | None) -> "PriceQuoteDTO | None":
        if quote is None:
            return None
        return cls(platinum=quote.platinum, rank=quote.rank)


class ItemPriceDTO(BaseModel):
    """物品市價；沒有線上賣單或收購單時對應欄位為 null"""

    slug: str
    rank: int | None = None
    lowest_sell: PriceQuoteDTO | None = None
    highest_buy: PriceQuoteDTO | None = None
    updated_at: datetime

    @classmethod
    def from_domain(cls, price: ItemPrice) -> "ItemPriceDTO":
        return cls(
            slug=price.slug,
            rank=price.rank,
            lowest_sell=PriceQuoteDTO.from_domain(price.lowest_sell),
            highest_buy=PriceQuoteDTO.from_domain(price.highest_buy),
            updated_at=price.updated_at,
        )
