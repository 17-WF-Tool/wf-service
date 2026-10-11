import json
import sys
import time
from pathlib import Path
from typing import Any

from curl_cffi import requests

BASE_URL = "https://api.warframe.market/v2"
FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

DEFAULT_USERNAME = "rrrrrrrrrrrrrrrrr_17"
TOP_ORDERS_SLUG = "primed_continuity"
TOP_ORDERS_LIMIT = 3
# 除了使用者掛單引用的物品外，額外保留的物品
EXTRA_ITEM_SLUGS = ("primed_continuity", "vadarya_prime_blueprint")
KEPT_USER_FIELDS = ("id", "ingameName", "slug", "platform", "crossplay", "status")


def fetch(path: str, language: str = "en") -> tuple[int, dict[str, Any]]:
    response = requests.get(
        f"{BASE_URL}{path}",
        headers={"language": language, "platform": "pc", "crossplay": "true"},
        impersonate="chrome124",
        timeout=30,
    )
    # 遵守官方請求頻率限制
    time.sleep(0.5)
    return response.status_code, response.json()


def save(name: str, payload: dict[str, Any]) -> None:
    path = FIXTURES_DIR / name
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"已寫入 {path.relative_to(FIXTURES_DIR.parent.parent)}")


def trim_user(order: dict[str, Any]) -> dict[str, Any]:
    user = order.get("user")
    if user:
        order["user"] = {k: user[k] for k in KEPT_USER_FIELDS if k in user}
    return order


def main(username: str) -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    _, versions = fetch("/versions")
    save("versions.json", versions)

    _, user_orders = fetch(f"/orders/user/{username}")
    save("user_orders.json", user_orders)

    _, not_found = fetch("/orders/user/__no_such_user_for_fixture__")
    save("error_user_not_found.json", not_found)

    _, top = fetch(f"/orders/item/{TOP_ORDERS_SLUG}/top")
    for side in ("sell", "buy"):
        top["data"][side] = [trim_user(o) for o in top["data"][side][:TOP_ORDERS_LIMIT]]
    save(f"top_orders_{TOP_ORDERS_SLUG}.json", top)

    item_ids = {o["itemId"] for o in user_orders["data"]}
    for language in ("zh-hant", "zh-hans"):
        _, items = fetch("/items", language=language)
        items["data"] = [
            i
            for i in items["data"]
            if i["id"] in item_ids or i["slug"] in EXTRA_ITEM_SLUGS
        ]
        save(f"items_{language}.json", items)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_USERNAME)
