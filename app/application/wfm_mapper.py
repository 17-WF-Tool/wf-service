import logging
from datetime import datetime
from typing import Any

from app.config import settings
from app.domain.market_item import ItemNames, MarketItem
from app.domain.order import Order, OrderType

logger = logging.getLogger(__name__)


def to_market_item(
    raw: dict[str, Any],
    assets_base_url: str = settings.WF_MARKET_ASSETS_URL,
) -> MarketItem:
    """轉換 /v2/items 的單筆物品

    i18n 可同時包含 en、zh-hant、zh-hans；官方一次只回傳 en 與一種中文，
    合併多語由呼叫端負責。圖片取自 en，各語系的圖片路徑相同。
    """
    i18n = raw.get("i18n", {})
    en = i18n.get("en", {})

    names = ItemNames(
        en=en.get("name") or raw["slug"],
        zh_hant=i18n.get("zh-hant", {}).get("name"),
        zh_hans=i18n.get("zh-hans", {}).get("name"),
    )

    return MarketItem(
        id=raw["id"],
        slug=raw["slug"],
        names=names,
        tags=tuple(raw.get("tags", [])),
        game_ref=raw.get("gameRef"),
        thumb=_asset_url(en.get("thumb"), assets_base_url),
        icon=_asset_url(en.get("icon"), assets_base_url),
        sub_icon=_asset_url(en.get("subIcon"), assets_base_url),
        max_rank=raw.get("maxRank"),
        ducats=raw.get("ducats"),
        vaulted=raw.get("vaulted"),
        bulk_tradable=raw.get("bulkTradable"),
        subtypes=tuple(raw.get("subtypes", [])),
    )


def to_order(raw: dict[str, Any]) -> Order:
    """轉換 /v2/orders/... 的單筆掛單"""
    return Order(
        id=raw["id"],
        type=OrderType(raw["type"]),
        item_id=raw["itemId"],
        platinum=raw["platinum"],
        quantity=raw["quantity"],
        per_trade=raw.get("perTrade", 1),
        rank=raw.get("rank"),
        subtype=raw.get("subtype"),
        visible=raw.get("visible", True),
        created_at=_parse_datetime(raw.get("createdAt")),
        updated_at=_parse_datetime(raw.get("updatedAt")),
    )


def to_orders(raws: list[dict[str, Any]]) -> list[Order]:
    """轉換多筆掛單，單筆格式異常時略過並記錄，不影響整份列表"""
    orders = []
    for raw in raws:
        try:
            orders.append(to_order(raw))
        except (KeyError, TypeError, ValueError) as e:
            logger.warning("略過無法轉換的掛單 %s: %r", raw.get("id"), e)
    return orders


def _asset_url(path: str | None, base_url: str) -> str | None:
    # 新物品的 thumb 可能為空字串
    if not path:
        return None
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)
