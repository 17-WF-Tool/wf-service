import pytest
from fastapi.testclient import TestClient

import main
from app.adapters.inbound.rest.router import get_item_service, get_price_service
from app.adapters.outbound.in_memory_repo import InMemoryItemRepository
from app.application.catalog_service import CatalogService
from app.application.item_service import ItemService
from app.application.price_service import PriceService
from main import app
from tests.support import FakeMarketClient


@pytest.fixture
def fake_client() -> FakeMarketClient:
    return FakeMarketClient()


@pytest.fixture
async def loaded_catalog() -> CatalogService:
    """已載入 fixtures 物品的目錄，使用獨立的假 client，不影響測試的呼叫紀錄"""
    catalog = CatalogService(FakeMarketClient())
    await catalog.refresh()
    return catalog


@pytest.fixture
def make_service(loaded_catalog):
    """建立使用假 client 的 ItemService"""

    def _make(
        client: FakeMarketClient | None = None,
        default_username: str = "",
        catalog: CatalogService | None = None,
    ):
        return ItemService(
            repo=InMemoryItemRepository(),
            market_client=client or FakeMarketClient(),
            catalog=catalog if catalog is not None else loaded_catalog,
            default_username=default_username,
        )

    return _make


@pytest.fixture
def app_catalog(monkeypatch) -> CatalogService:
    """取代 main 的物品目錄，避免 API 測試啟動時連線官方"""
    catalog = CatalogService(FakeMarketClient())
    monkeypatch.setattr(main, "catalog_service", catalog)
    return catalog


@pytest.fixture
def api_client(app_catalog):
    """建立 API 測試 client，以 use_service() 注入使用假 client 的 service"""
    providers = (get_item_service, get_price_service)
    originals = {p: app.dependency_overrides.get(p) for p in providers}

    with TestClient(app) as client:

        def use_service(
            service: ItemService | None = None,
            *,
            price_service: PriceService | None = None,
        ) -> TestClient:
            if service is not None:
                app.dependency_overrides[get_item_service] = lambda: service
            if price_service is not None:
                app.dependency_overrides[get_price_service] = lambda: price_service
            return client

        yield use_service

    for provider, original in originals.items():
        if original is None:
            app.dependency_overrides.pop(provider, None)
        else:
            app.dependency_overrides[provider] = original
