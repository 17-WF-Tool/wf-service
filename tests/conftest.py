import pytest
from fastapi.testclient import TestClient

from app.adapters.inbound.rest.router import get_item_service
from app.adapters.outbound.in_memory_repo import InMemoryItemRepository
from app.application.item_service import ItemService
from main import app
from tests.support import FakeMarketClient


@pytest.fixture
def fake_client() -> FakeMarketClient:
    return FakeMarketClient()


@pytest.fixture
def make_service():
    """建立使用假 client 的 ItemService"""

    def _make(client: FakeMarketClient | None = None, default_username: str = ""):
        return ItemService(
            repo=InMemoryItemRepository(),
            market_client=client or FakeMarketClient(),
            default_username=default_username,
        )

    return _make


@pytest.fixture
def api_client():
    """建立 API 測試 client，以 use_service() 注入使用假 client 的 service"""
    original = app.dependency_overrides.get(get_item_service)

    with TestClient(app) as client:

        def use_service(service: ItemService) -> TestClient:
            app.dependency_overrides[get_item_service] = lambda: service
            return client

        yield use_service

    if original is None:
        app.dependency_overrides.pop(get_item_service, None)
    else:
        app.dependency_overrides[get_item_service] = original
