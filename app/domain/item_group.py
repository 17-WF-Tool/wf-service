from dataclasses import dataclass

from app.domain.market_item import ItemNames


@dataclass(frozen=True)
class ItemGroup:
    """本專案維護的物品分組，官方沒有商人或勢力的分組資料"""

    id: str
    names: ItemNames
    slugs: tuple[str, ...] = ()
