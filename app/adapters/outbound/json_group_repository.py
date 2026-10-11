import json
from pathlib import Path
from typing import Any

from app.domain.item_group import ItemGroup
from app.domain.market_item import ItemNames
from app.ports.group_repository_port import GroupRepositoryPort


class JsonGroupRepository(GroupRepositoryPort):
    """從 JSON 檔讀取分組，格式為 {"groups": [{id, names, slugs, ...}]}

    建立時即讀取並檢查，格式錯誤或分組 id 重複時丟 ValueError。
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._groups = _parse(json.loads(self.path.read_text(encoding="utf-8")))

    def list_groups(self) -> list[ItemGroup]:
        return list(self._groups)


def _parse(payload: dict[str, Any]) -> list[ItemGroup]:
    groups = []
    seen: set[str] = set()
    for raw in payload.get("groups", []):
        try:
            names = raw["names"]
            group = ItemGroup(
                id=raw["id"],
                names=ItemNames(
                    en=names["en"],
                    zh_hant=names.get("zh_hant"),
                    zh_hans=names.get("zh_hans"),
                ),
                # 去除重複並保留原順序
                slugs=tuple(dict.fromkeys(raw.get("slugs", []))),
            )
        except (KeyError, TypeError) as e:
            raise ValueError(f"分組資料格式錯誤: {raw!r}") from e
        if group.id in seen:
            raise ValueError(f"分組 id 重複: {group.id}")
        seen.add(group.id)
        groups.append(group)
    return groups
