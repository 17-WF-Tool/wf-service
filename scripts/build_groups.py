"""依 WFCD 物品資料產生 data/groups.json 中的自動分組

- 自動分組（source 為 wfcd）：依 WFCD drops 的 location 前綴找出物品，再以英文名稱對應 WFM slug
- 手動分組（source 為 manual）：原樣保留，例如會輪替商品的 Baro Ki'Teer
"""

import json
import time
from pathlib import Path
from typing import Any

from curl_cffi import requests

WFM_ITEMS_URL = "https://api.warframe.market/v2/items"
# 固定版本：1.1276.19 起部分物品缺少 drops 欄位，無法判斷來源
WFCD_VERSION = "1.1276.3"
WFCD_URL = (
    f"https://cdn.jsdelivr.net/npm/@wfcd/items@{WFCD_VERSION}/data/json/{{name}}.json"
)
WFCD_FILES = ("Mods", "Primary", "Secondary", "Melee", "Arcanes", "Misc")
GROUPS_FILE = Path(__file__).resolve().parent.parent / "data" / "groups.json"

ACOLYTES = ("Angst", "Malice", "Mania", "Misery", "Torment", "Violence")

# 名稱取自遊戲內集團浮印的官方譯名
GENERATED_GROUPS: list[dict[str, Any]] = [
    {
        "id": "steel_meridian",
        "names": {"en": "Steel Meridian", "zh_hant": "鋼鐵防線", "zh_hans": "钢铁防线"},
        "locations": ("Steel Meridian,",),
    },
    {
        "id": "arbiters_of_hexis",
        "names": {
            "en": "Arbiters of Hexis",
            "zh_hant": "均衡仲裁者",
            "zh_hans": "均衡仲裁者",
        },
        "locations": ("Arbiters of Hexis,",),
    },
    {
        "id": "cephalon_suda",
        "names": {"en": "Cephalon Suda", "zh_hant": "中樞蘇達", "zh_hans": "中枢苏达"},
        "locations": ("Cephalon Suda,",),
    },
    {
        "id": "the_perrin_sequence",
        "names": {
            "en": "The Perrin Sequence",
            "zh_hant": "佩蘭數列",
            "zh_hans": "佩兰数列",
        },
        "locations": ("The Perrin Sequence,",),
    },
    {
        "id": "red_veil",
        "names": {"en": "Red Veil", "zh_hant": "血色面紗", "zh_hans": "血色面纱"},
        "locations": ("Red Veil,",),
    },
    {
        "id": "new_loka",
        "names": {"en": "New Loka", "zh_hant": "新世間", "zh_hans": "新世间"},
        "locations": ("New Loka,",),
    },
    {
        "id": "steel_path_acolytes",
        "names": {
            "en": "Steel Path Acolytes",
            "zh_hant": "鋼鐵之路追隨者",
            "zh_hans": "钢铁之路追随者",
        },
        "locations": tuple(f"{name} (" for name in ACOLYTES),
    },
]


def fetch_json(url: str, **kwargs: Any) -> Any:
    response = requests.get(url, impersonate="chrome124", timeout=60, **kwargs)
    response.raise_for_status()
    # 遵守官方請求頻率限制
    time.sleep(0.5)
    return response.json()


def wfm_slugs_by_name() -> dict[str, str]:
    payload = fetch_json(WFM_ITEMS_URL, headers={"language": "en", "platform": "pc"})
    return {i["i18n"]["en"]["name"].lower(): i["slug"] for i in payload["data"]}


def wfcd_items() -> list[dict[str, Any]]:
    items = []
    for name in WFCD_FILES:
        items.extend(fetch_json(WFCD_URL.format(name=name)))
    return items


def build_group(
    spec: dict[str, Any], items: list[dict[str, Any]], slugs: dict[str, str]
) -> dict[str, Any]:
    matched = set()
    for item in items:
        locations = [d.get("location", "") for d in item.get("drops") or []]
        if any(loc.startswith(spec["locations"]) for loc in locations):
            slug = slugs.get(item["name"].lower())
            # WFM 沒有的物品（不可交易）略過
            if slug:
                matched.add(slug)
    return {
        "id": spec["id"],
        "names": spec["names"],
        "source": "wfcd",
        "slugs": sorted(matched),
    }


def main() -> None:
    existing = json.loads(GROUPS_FILE.read_text(encoding="utf-8"))["groups"]
    manual = [g for g in existing if g.get("source") == "manual"]

    slugs = wfm_slugs_by_name()
    items = wfcd_items()
    generated = [build_group(spec, items, slugs) for spec in GENERATED_GROUPS]

    GROUPS_FILE.write_text(
        json.dumps({"groups": manual + generated}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for group in generated:
        print(f"{group['id']}: {len(group['slugs'])} 筆")
    print(f"已寫入 {GROUPS_FILE}")


if __name__ == "__main__":
    main()
