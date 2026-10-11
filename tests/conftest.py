import pytest
from fastapi.testclient import TestClient

import main
from app.adapters.inbound.rest.router import (
    get_group_service,
    get_order_service,
    get_price_service,
)
from app.adapters.outbound.json_group_repository import JsonGroupRepository
from app.application.catalog_service import CatalogService
from app.application.group_service import GroupService
from app.application.order_service import OrderService
from app.application.price_service import PriceService
from app.config import settings
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
    """建立使用假 client 的 OrderService"""

    def _make(
        client: FakeMarketClient | None = None,
        default_username: str = "",
        catalog: CatalogService | None = None,
    ):
        return OrderService(
            market_client=client or FakeMarketClient(),
            catalog=catalog if catalog is not None else loaded_catalog,
            default_username=default_username,
        )

    return _make


@pytest.fixture
def app_catalog(monkeypatch) -> CatalogService:
    """取代 main 的物品目錄，避免 API 測試啟動時連線官方

    main 的分組服務一併改用此目錄，讓啟動時的 slug 檢查對照同一份資料。
    """
    catalog = CatalogService(FakeMarketClient())
    monkeypatch.setattr(main, "catalog_service", catalog)
    groups = GroupService(JsonGroupRepository(settings.GROUPS_FILE), catalog)
    monkeypatch.setattr(main, "group_service", groups)
    return catalog


@pytest.fixture
def api_client(app_catalog):
    """建立 API 測試 client，以 use_service() 注入使用假 client 的 service"""
    providers = (get_order_service, get_price_service, get_group_service)
    originals = {p: app.dependency_overrides.get(p) for p in providers}

    with TestClient(app) as client:

        def use_service(
            service: OrderService | None = None,
            *,
            price_service: PriceService | None = None,
            group_service: GroupService | None = None,
        ) -> TestClient:
            if service is not None:
                app.dependency_overrides[get_order_service] = lambda: service
            if price_service is not None:
                app.dependency_overrides[get_price_service] = lambda: price_service
            if group_service is not None:
                app.dependency_overrides[get_group_service] = lambda: group_service
            return client

        yield use_service

    for provider, original in originals.items():
        if original is None:
            app.dependency_overrides.pop(provider, None)
        else:
            app.dependency_overrides[provider] = original
