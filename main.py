import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.inbound.rest.router import (
    get_group_service,
    get_order_service,
    get_price_service,
)
from app.adapters.inbound.rest.router import router as market_router
from app.adapters.outbound.json_group_repository import JsonGroupRepository
from app.adapters.outbound.wf_market_client import WarframeMarketClient
from app.application.catalog_service import CatalogService
from app.application.group_service import GroupService
from app.application.order_service import OrderService
from app.application.price_service import PriceService
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 啟動時預熱物品目錄、檢查分組 slug 並開始定期檢查版本，關閉時停止
    await catalog_service.warm_up()
    group_service.find_unknown_slugs()
    catalog_service.start_periodic_refresh()
    yield
    await catalog_service.stop_periodic_refresh()


app = FastAPI(
    lifespan=lifespan,
    title="Warframe Market Controller API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 跨域存取設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.ALLOWED_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 組裝依賴關係 (Composition Root)
market_client = WarframeMarketClient(
    base_url=settings.WF_MARKET_API_URL,
    min_request_interval=settings.WF_MARKET_MIN_REQUEST_INTERVAL,
)
catalog_service = CatalogService(
    market_client,
    refresh_interval=settings.CATALOG_REFRESH_INTERVAL,
    miss_refresh_cooldown=settings.CATALOG_MISS_REFRESH_COOLDOWN,
)
order_service = OrderService(
    market_client=market_client,
    catalog=catalog_service,
    default_username=settings.DEFAULT_WF_USERNAME,
)
price_service = PriceService(market_client, cache_ttl=settings.PRICE_CACHE_TTL)
group_service = GroupService(
    JsonGroupRepository(settings.GROUPS_FILE), catalog=catalog_service
)

# 注入到 FastAPI 路由
app.dependency_overrides[get_order_service] = lambda: order_service
app.dependency_overrides[get_price_service] = lambda: price_service
app.dependency_overrides[get_group_service] = lambda: group_service

# 掛載路由
app.include_router(market_router)


@app.get("/")
def health_check():
    return {"status": "ok", "app": "Warframe Market Controller Backend"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=settings.API_PORT, reload=True)
