import asyncio
import time
from collections.abc import Callable
from datetime import UTC, datetime

from app.application.wfm_mapper import to_orders
from app.domain.item_price import ItemPrice, PriceQuote
from app.domain.order import Order
from app.ports.market_client_port import MarketClientPort
from app.ports.price_service_port import PriceServicePort

CacheKey = tuple[str, int | None]


class PriceService(PriceServicePort):
    """物品市價查詢，同一物品與等級在快取時間內不重複打官方"""

    def __init__(
        self,
        market_client: MarketClientPort,
        *,
        cache_ttl: float = 300,
        clock: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self.market_client = market_client
        self.cache_ttl = cache_ttl
        self._clock = clock
        self._now = now
        self._cache: dict[CacheKey, tuple[float, ItemPrice]] = {}
        self._locks: dict[CacheKey, asyncio.Lock] = {}

    async def get_item_price(self, slug: str, rank: int | None = None) -> ItemPrice:
        key = (slug.strip().lower(), rank)
        cached = self._get_cached(key)
        if cached is not None:
            return cached

        # 同一物品同時多個查詢只打一次官方，其餘等待結果
        lock = self._locks.setdefault(key, asyncio.Lock())
        try:
            async with lock:
                cached = self._get_cached(key)
                if cached is not None:
                    return cached
                price = await self._fetch(*key)
                self._store(key, price)
                return price
        finally:
            if not lock.locked() and self._locks.get(key) is lock:
                del self._locks[key]

    async def _fetch(self, slug: str, rank: int | None) -> ItemPrice:
        top = await self.market_client.fetch_top_orders(slug, rank=rank)
        sell = to_orders(top.get("sell", []))
        buy = to_orders(top.get("buy", []))
        return ItemPrice(
            slug=slug,
            rank=rank,
            lowest_sell=_quote(min(sell, key=lambda o: o.platinum, default=None)),
            highest_buy=_quote(max(buy, key=lambda o: o.platinum, default=None)),
            updated_at=self._now(),
        )

    def _get_cached(self, key: CacheKey) -> ItemPrice | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        stored_at, price = entry
        if self._clock() - stored_at >= self.cache_ttl:
            return None
        return price

    def _store(self, key: CacheKey, price: ItemPrice) -> None:
        now = self._clock()
        # 順便清掉過期項目，避免查詢過的物品無限累積
        expired = [k for k, (t, _) in self._cache.items() if now - t >= self.cache_ttl]
        for k in expired:
            del self._cache[k]
        self._cache[key] = (now, price)


def _quote(order: Order | None) -> PriceQuote | None:
    if order is None:
        return None
    return PriceQuote(platinum=order.platinum, rank=order.rank)
