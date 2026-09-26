import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.inbound.rest.router import get_item_service
from app.adapters.inbound.rest.router import router as market_router
from app.adapters.outbound.in_memory_repo import InMemoryItemRepository
from app.adapters.outbound.wf_market_client import WarframeMarketClient
from app.application.item_service import ItemService
from app.config import settings

app = FastAPI(
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
item_repo = InMemoryItemRepository()
market_client = WarframeMarketClient(base_url=settings.WF_MARKET_API_URL)
item_service = ItemService(
    repo=item_repo,
    market_client=market_client,
    default_username=settings.DEFAULT_WF_USERNAME,
)

# 注入到 FastAPI 路由
app.dependency_overrides[get_item_service] = lambda: item_service

# 掛載路由
app.include_router(market_router)


@app.get("/")
def health_check():
    return {"status": "ok", "app": "Warframe Market Controller Backend"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=settings.API_PORT, reload=True)
