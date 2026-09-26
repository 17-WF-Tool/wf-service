from typing import Any

from app.domain.item import Item
from app.ports.item_repository_port import ItemRepositoryPort
from app.ports.item_service_port import ItemServicePort
from app.ports.market_client_port import MarketClientPort


class ItemService(ItemServicePort):
    def __init__(
        self,
        repo: ItemRepositoryPort,
        market_client: MarketClientPort,
        default_username: str = "",
    ):
        self.repo = repo
        self.market_client = market_client
        self.default_username = default_username

    async def list_items_by_category(self, category: str) -> list[Item]:
        return await self.repo.get_by_category(category)

    async def update_item_price(self, item_id: str, new_price: int) -> Item:
        item = await self.repo.get_by_id(item_id)
        if not item:
            raise KeyError(f"找不到 ID 為 {item_id} 的物品")
        item.update_user_price(new_price)
        await self.repo.save(item)
        return item

    async def toggle_item_visibility(self, item_id: str, is_visible: bool) -> Item:
        item = await self.repo.get_by_id(item_id)
        if not item:
            raise KeyError(f"找不到 ID 為 {item_id} 的物品")
        item.set_visibility(is_visible)
        await self.repo.save(item)
        return item

    async def get_my_public_orders(
        self, username: str | None = None
    ) -> list[dict[str, Any]]:
        target_user = username or self.default_username
        if not target_user:
            raise ValueError("未指定使用者名稱，請於 config 設定或以參數傳入 username")

        raw_orders = await self.market_client.fetch_user_public_orders(target_user)

        formatted_orders = []
        for order in raw_orders:
            # 官方 v2 結構可能直接帶 itemId / item (含 en.name 或 urlName)
            item_info = order.get("item", {})

            name_en = (
                item_info.get("en", {}).get("name")
                or item_info.get("en", {}).get("item_name")
                or order.get("item", {}).get("url_name", "")
                or order.get("itemId", "")
            )

            # 將底線格式化為標準標題命名 (例如 "primed_continuity" -> "Primed Continuity")
            if "_" in name_en:
                name_en = name_en.replace("_", " ").title()

            formatted_orders.append(
                {
                    "order_id": order.get("id", ""),
                    "name_en": name_en or "Unknown Item",
                    "platinum": order.get("platinum", 0),
                    "quantity": order.get("quantity", 1),
                    "order_type": order.get("type", "sell"),
                    "is_visible": order.get("visible", True),
                    "mod_rank": order.get("modRank")
                    or order.get("mod_rank"),  # v2 常用駝峰命名
                }
            )

        return formatted_orders
