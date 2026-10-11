import logging

from app.application.catalog_service import CatalogService
from app.domain.item_group import ItemGroup
from app.domain.market_item import MarketItem
from app.ports.group_repository_port import GroupRepositoryPort
from app.ports.group_service_port import GroupServicePort

logger = logging.getLogger(__name__)


class GroupService(GroupServicePort):
    def __init__(self, repo: GroupRepositoryPort, catalog: CatalogService):
        self.catalog = catalog
        self._groups = {group.id: group for group in repo.list_groups()}

    def list_groups(self) -> list[ItemGroup]:
        return list(self._groups.values())

    def get_group_items(self, group_id: str) -> list[MarketItem]:
        group = self._groups.get(group_id)
        if group is None:
            raise KeyError(f"找不到分組: {group_id}")
        items = (self.catalog.get_by_slug(slug) for slug in group.slugs)
        return [item for item in items if item is not None]

    def find_unknown_slugs(self) -> dict[str, list[str]]:
        """檢查各分組中不存在於物品目錄的 slug 並記錄警告；目錄未載入時略過"""
        if not self.catalog.is_loaded:
            logger.warning("物品目錄未載入，略過分組 slug 檢查")
            return {}

        unknown = {}
        for group in self._groups.values():
            missing = [s for s in group.slugs if self.catalog.get_by_slug(s) is None]
            if missing:
                unknown[group.id] = missing
                logger.warning(
                    "分組 %s 有 %d 個 slug 不在物品目錄中: %s",
                    group.id,
                    len(missing),
                    ", ".join(missing),
                )
        return unknown
