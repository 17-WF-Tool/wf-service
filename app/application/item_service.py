from app.application.catalog_service import CatalogService
from app.application.wfm_mapper import to_orders
from app.domain.item import Item
from app.domain.order import OrderType
from app.domain.order_listing import OrderListing
from app.ports.item_repository_port import ItemRepositoryPort
from app.ports.item_service_port import ItemServicePort
from app.ports.market_client_port import MarketClientPort


class ItemService(ItemServicePort):
    def __init__(
        self,
        repo: ItemRepositoryPort,
        market_client: MarketClientPort,
        catalog: CatalogService,
        default_username: str = "",
    ):
        self.repo = repo
        self.market_client = market_client
        self.catalog = catalog
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

    async def get_user_orders(
        self,
        username: str | None = None,
        order_type: OrderType | None = None,
    ) -> list[OrderListing]:
        target_user = username or self.default_username
        if not target_user:
            raise ValueError("未指定使用者名稱，請於 config 設定或以參數傳入 username")

        raw_orders = await self.market_client.fetch_user_orders(target_user)
        orders = [
            order
            for order in to_orders(raw_orders)
            if order_type is None or order.type == order_type
        ]
        return [
            OrderListing(order=order, item=await self.catalog.resolve(order.item_id))
            for order in orders
        ]
