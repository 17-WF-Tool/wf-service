import asyncio
import logging
import time
from collections.abc import Callable, Iterable
from typing import Any

from app.application.wfm_mapper import to_market_item
from app.domain.market_item import MarketItem
from app.ports.market_client_port import MarketClientPort

logger = logging.getLogger(__name__)

# 官方 /items 一次只回傳 en 與一種語言，需各抓一次再合併
CATALOG_LANGUAGES = ("zh-hant", "zh-hans")


class CatalogService:
    """官方物品目錄的記憶體快取

    - 以 itemId 為 key 保存三語合併後的 MarketItem
    - 依 /versions 的 collections.items 判斷是否需要重新下載
    - 更新失敗時保留舊資料
    """

    def __init__(
        self,
        market_client: MarketClientPort,
        *,
        refresh_interval: float = 3600,
        miss_refresh_cooldown: float = 300,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.market_client = market_client
        self.refresh_interval = refresh_interval
        self.miss_refresh_cooldown = miss_refresh_cooldown
        self._clock = clock

        self._items_by_id: dict[str, MarketItem] = {}
        self._items_by_slug: dict[str, MarketItem] = {}
        self._version: str | None = None
        self._lock = asyncio.Lock()
        self._last_miss_refresh: float | None = None
        self._refresh_task: asyncio.Task | None = None

    # ---------- 狀態 ----------

    @property
    def is_loaded(self) -> bool:
        return bool(self._items_by_id)

    @property
    def version(self) -> str | None:
        return self._version

    def __len__(self) -> int:
        return len(self._items_by_id)

    # ---------- 查詢 ----------

    def get_by_id(self, item_id: str) -> MarketItem | None:
        return self._items_by_id.get(item_id)

    def get_by_slug(self, slug: str) -> MarketItem | None:
        return self._items_by_slug.get(slug)

    def filter_by_tags(self, *tags: str) -> list[MarketItem]:
        """回傳同時具有所有指定標籤的物品；未指定標籤時回傳全部"""
        return [
            item
            for item in self._items_by_id.values()
            if all(item.has_tag(tag) for tag in tags)
        ]

    async def resolve(self, item_id: str) -> MarketItem | None:
        """依 itemId 取得物品；查不到時在冷卻時間外觸發一次更新後再查"""
        item = self.get_by_id(item_id)
        if item is not None or not self._can_refresh_on_miss():
            return item

        # 先記錄時間再更新，避免同時多個查詢都觸發
        self._last_miss_refresh = self._clock()
        logger.info("物品目錄查無 %s，檢查是否有更新", item_id)
        try:
            await self.refresh()
        except (KeyError, RuntimeError) as e:
            logger.warning("物品目錄更新失敗，沿用現有資料: %s", e)
        return self.get_by_id(item_id)

    # ---------- 更新 ----------

    async def refresh(self, *, force: bool = False) -> bool:
        """檢查版本並視需要重新下載，回傳是否有重新下載

        失敗時丟出 KeyError 或 RuntimeError，現有資料不受影響。
        """
        async with self._lock:
            versions = await self.market_client.fetch_versions()
            version = versions.get("collections", {}).get("items")

            if not force and self.is_loaded and version == self._version:
                logger.debug("物品目錄版本未變更（%s），略過下載", version)
                return False

            items = await self._download()
            self._items_by_id = {item.id: item for item in items}
            self._items_by_slug = {item.slug: item for item in items}
            self._version = version
            logger.info("物品目錄已載入 %d 筆（版本 %s）", len(items), version)
            return True

    async def warm_up(self) -> None:
        """啟動時預熱；失敗只記錄錯誤，不中斷啟動，留待定期更新重試"""
        try:
            await self.refresh(force=True)
        except (KeyError, RuntimeError) as e:
            logger.error("物品目錄預熱失敗，將於下次定期檢查時重試: %s", e)

    def start_periodic_refresh(self) -> None:
        if self._refresh_task is None or self._refresh_task.done():
            self._refresh_task = asyncio.create_task(self._periodic_refresh())

    async def stop_periodic_refresh(self) -> None:
        task, self._refresh_task = self._refresh_task, None
        if task is None:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    # ---------- 內部 ----------

    async def _periodic_refresh(self) -> None:
        while True:
            await asyncio.sleep(self.refresh_interval)
            try:
                await self.refresh()
            except Exception:
                # 任何錯誤都不能讓背景工作停止
                logger.exception("物品目錄定期更新失敗")

    async def _download(self) -> list[MarketItem]:
        merged: dict[str, dict[str, Any]] = {}
        for language in CATALOG_LANGUAGES:
            for raw in await self.market_client.fetch_items(language):
                _merge_i18n(merged, raw)
        return list(_to_items(merged.values()))

    def _can_refresh_on_miss(self) -> bool:
        if self._last_miss_refresh is None:
            return True
        return self._clock() - self._last_miss_refresh >= self.miss_refresh_cooldown


def _merge_i18n(merged: dict[str, dict[str, Any]], raw: dict[str, Any]) -> None:
    existing = merged.get(raw.get("id"))
    if existing is None:
        merged[raw.get("id")] = {**raw, "i18n": dict(raw.get("i18n", {}))}
    else:
        existing["i18n"].update(raw.get("i18n", {}))


def _to_items(raws: Iterable[dict[str, Any]]) -> Iterable[MarketItem]:
    for raw in raws:
        try:
            yield to_market_item(raw)
        except (KeyError, TypeError, ValueError) as e:
            # 單筆格式異常不影響整份目錄
            logger.warning("略過無法轉換的物品 %s: %r", raw.get("id"), e)
