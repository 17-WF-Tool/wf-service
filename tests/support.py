"""測試共用工具：讀取官方回應 fixtures 與假的 MarketClient"""

import copy
import json
from functools import cache
from pathlib import Path
from typing import Any

from app.domain.item_group import ItemGroup
from app.domain.market_item import ItemNames
from app.ports.group_repository_port import GroupRepositoryPort
from app.ports.market_client_port import MarketClientPort

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@cache
def _read_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def load_fixture(name: str) -> dict[str, Any]:
    """讀取完整的官方回應外殼 {apiVersion, data, error}，每次回傳獨立副本"""
    return copy.deepcopy(_read_fixture(name))


def load_data(name: str) -> Any:
    """只讀取官方回應中的 data"""
    return load_fixture(name)["data"]


def merged_raw_items() -> list[dict[str, Any]]:
    """合併繁中與簡中兩份物品目錄的 i18n，模擬三語齊全的原始資料"""
    hans_by_id = {i["id"]: i for i in load_data("items_zh-hans.json")}
    merged = load_data("items_zh-hant.json")
    for raw in merged:
        raw["i18n"] |= hans_by_id.get(raw["id"], {}).get("i18n", {})
    return merged


def make_group(group_id: str, *slugs: str) -> ItemGroup:
    return ItemGroup(
        id=group_id,
        names=ItemNames(en=group_id.title(), zh_hant=f"{group_id} 繁"),
        slugs=slugs,
    )


class StaticGroupRepository(GroupRepositoryPort):
    def __init__(self, groups: list[ItemGroup]):
        self.groups = groups

    def list_groups(self) -> list[ItemGroup]:
        return list(self.groups)


class FakeMarketClient(MarketClientPort):
    """以 fixtures 回應的假 client，不連網

    - 各方法的回傳值可由建構子覆寫
    - errors 指定方法名稱對應要丟出的例外
    - calls 記錄呼叫歷程，供驗證快取等行為
    """

    def __init__(
        self,
        *,
        user_orders: list[dict[str, Any]] | None = None,
        top_orders: dict[str, list[dict[str, Any]]] | None = None,
        versions: dict[str, Any] | None = None,
        items: dict[str, list[dict[str, Any]]] | None = None,
        errors: dict[str, Exception] | None = None,
    ):
        self.user_orders = (
            user_orders if user_orders is not None else load_data("user_orders.json")
        )
        self.top_orders = (
            top_orders
            if top_orders is not None
            else load_data("top_orders_primed_continuity.json")
        )
        self.versions = versions if versions is not None else load_data("versions.json")
        # 依語言覆寫物品目錄，未指定的語言讀取 fixtures
        self.items = items or {}
        self.errors = errors or {}
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def _record(self, method: str, *args: Any) -> None:
        self.calls.append((method, args))
        if method in self.errors:
            raise self.errors[method]

    async def fetch_versions(self) -> dict[str, Any]:
        self._record("fetch_versions")
        return copy.deepcopy(self.versions)

    async def fetch_items(self, language: str = "zh-hant") -> list[dict[str, Any]]:
        self._record("fetch_items", language)
        if language in self.items:
            return copy.deepcopy(self.items[language])
        return load_data(f"items_{language}.json")

    def call_count(self, method: str) -> int:
        return sum(1 for name, _ in self.calls if name == method)

    def set_items_version(self, version: str) -> None:
        """模擬官方物品目錄更新"""
        self.versions["collections"]["items"] = version

    async def fetch_user_orders(self, username: str) -> list[dict[str, Any]]:
        self._record("fetch_user_orders", username)
        return copy.deepcopy(self.user_orders)

    async def fetch_top_orders(
        self, slug: str, rank: int | None = None
    ) -> dict[str, list[dict[str, Any]]]:
        self._record("fetch_top_orders", slug, rank)
        return copy.deepcopy(self.top_orders)
