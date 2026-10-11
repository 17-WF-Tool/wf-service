from app.application.catalog_service import CatalogService
from app.application.wfm_mapper import to_orders
from app.domain.order import OrderType
from app.domain.order_listing import OrderListing
from app.ports.market_client_port import MarketClientPort
from app.ports.order_service_port import OrderServicePort


class OrderService(OrderServicePort):
    def __init__(
        self,
        market_client: MarketClientPort,
        catalog: CatalogService,
        default_username: str = "",
    ):
        self.market_client = market_client
        self.catalog = catalog
        self.default_username = default_username

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
