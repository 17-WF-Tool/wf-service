import asyncio
import logging

import pytest

from app.application.catalog_service import CatalogService
from tests.support import FakeMarketClient, load_data

PRIMED_CONTINUITY_ID = "54c6855ee779891362942572"
VADARYA_ID = "68add07d731e63abe79a5d16"
FIXTURE_ITEM_COUNT = len(load_data("items_zh-hant.json"))


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def make_catalog(clock):
    def _make(client: FakeMarketClient | None = None, **kwargs) -> CatalogService:
        options = {"miss_refresh_cooldown": 300, "clock": clock} | kwargs
        return CatalogService(client or FakeMarketClient(), **options)

    return _make


@pytest.fixture
async def loaded(make_catalog, fake_client):
    catalog = make_catalog(fake_client)
    await catalog.refresh()
    fake_client.calls.clear()
    return catalog


class TestInitialState:
    def test_is_empty_before_refresh(self, make_catalog):
        catalog = make_catalog()

        assert not catalog.is_loaded
        assert len(catalog) == 0
        assert catalog.version is None
        assert catalog.get_by_id(PRIMED_CONTINUITY_ID) is None


class TestRefresh:
    async def test_downloads_both_languages_and_merges(self, make_catalog, fake_client):
        catalog = make_catalog(fake_client)

        reloaded = await catalog.refresh()

        assert reloaded
        assert len(catalog) == FIXTURE_ITEM_COUNT
        assert catalog.version == fake_client.versions["collections"]["items"]
        assert [args for name, args in fake_client.calls if name == "fetch_items"] == [
            ("zh-hant",),
            ("zh-hans",),
        ]
        item = catalog.get_by_id(VADARYA_ID)
        assert item.names.en == "Vadarya Prime Blueprint"
        assert item.names.zh_hant == "瓦達雅 Prime 藍圖"
        assert item.names.zh_hans == "瓦德雅 Prime 蓝图"

    async def test_skips_download_when_version_unchanged(self, loaded, fake_client):
        reloaded = await loaded.refresh()

        assert not reloaded
        assert fake_client.call_count("fetch_versions") == 1
        assert fake_client.call_count("fetch_items") == 0

    async def test_downloads_again_when_version_changes(self, loaded, fake_client):
        fake_client.set_items_version("new-version")

        reloaded = await loaded.refresh()

        assert reloaded
        assert loaded.version == "new-version"
        assert fake_client.call_count("fetch_items") == 2

    async def test_force_downloads_even_if_version_unchanged(self, loaded, fake_client):
        reloaded = await loaded.refresh(force=True)

        assert reloaded
        assert fake_client.call_count("fetch_items") == 2

    async def test_failure_keeps_existing_data(self, loaded, fake_client):
        fake_client.set_items_version("new-version")
        fake_client.errors["fetch_items"] = RuntimeError("HTTP 503")

        with pytest.raises(RuntimeError):
            await loaded.refresh()

        assert len(loaded) == FIXTURE_ITEM_COUNT
        assert loaded.version != "new-version"

    async def test_concurrent_refresh_downloads_once(self, make_catalog, fake_client):
        catalog = make_catalog(fake_client)

        results = await asyncio.gather(catalog.refresh(), catalog.refresh())

        assert sorted(results) == [False, True]
        assert fake_client.call_count("fetch_items") == 2

    async def test_includes_items_only_in_one_language(self, make_catalog):
        hant = load_data("items_zh-hant.json")
        extra = hant[0] | {"id": "only-hant", "slug": "only_hant_item"}
        client = FakeMarketClient(items={"zh-hant": [*hant, extra]})
        catalog = make_catalog(client)

        await catalog.refresh()

        item = catalog.get_by_id("only-hant")
        assert item is not None
        assert item.names.zh_hans is None

    async def test_skips_malformed_items(self, make_catalog, caplog):
        hant = load_data("items_zh-hant.json")
        client = FakeMarketClient(items={"zh-hant": [*hant, {"id": "broken"}]})
        catalog = make_catalog(client)

        with caplog.at_level(logging.WARNING):
            await catalog.refresh()

        assert len(catalog) == FIXTURE_ITEM_COUNT
        assert "broken" in caplog.text


class TestWarmUp:
    async def test_loads_catalog(self, make_catalog):
        catalog = make_catalog()

        await catalog.warm_up()

        assert len(catalog) == FIXTURE_ITEM_COUNT

    async def test_failure_does_not_raise(self, make_catalog, caplog):
        client = FakeMarketClient(errors={"fetch_versions": RuntimeError("down")})
        catalog = make_catalog(client)

        with caplog.at_level(logging.ERROR):
            await catalog.warm_up()

        assert not catalog.is_loaded
        assert "預熱失敗" in caplog.text


class TestQueries:
    def test_get_by_id_and_slug(self, loaded):
        by_id = loaded.get_by_id(PRIMED_CONTINUITY_ID)

        assert by_id.slug == "primed_continuity"
        assert loaded.get_by_slug("primed_continuity") is by_id
        assert loaded.get_by_slug("no_such_item") is None

    def test_filter_by_single_tag(self, loaded):
        blueprints = loaded.filter_by_tags("blueprint")

        assert blueprints
        assert all(item.has_tag("blueprint") for item in blueprints)

    def test_filter_requires_all_tags(self, loaded):
        items = loaded.filter_by_tags("mod", "legendary")

        assert [item.slug for item in items] == ["primed_continuity"]

    def test_filter_without_tags_returns_all(self, loaded):
        assert len(loaded.filter_by_tags()) == FIXTURE_ITEM_COUNT


class TestResolve:
    async def test_hit_does_not_call_client(self, loaded, fake_client):
        item = await loaded.resolve(PRIMED_CONTINUITY_ID)

        assert item.slug == "primed_continuity"
        assert fake_client.calls == []

    async def test_miss_checks_version_without_downloading(self, loaded, fake_client):
        item = await loaded.resolve("unknown-id")

        assert item is None
        assert fake_client.call_count("fetch_versions") == 1
        assert fake_client.call_count("fetch_items") == 0

    async def test_miss_finds_newly_added_item(self, loaded, fake_client):
        hant = load_data("items_zh-hant.json")
        new_item = hant[0] | {"id": "new-id", "slug": "new_item"}
        fake_client.items["zh-hant"] = [*hant, new_item]
        fake_client.set_items_version("new-version")

        item = await loaded.resolve("new-id")

        assert item.slug == "new_item"

    async def test_misses_within_cooldown_trigger_once(self, loaded, fake_client):
        await loaded.resolve("unknown-1")
        await loaded.resolve("unknown-2")

        assert fake_client.call_count("fetch_versions") == 1

    async def test_miss_after_cooldown_triggers_again(self, loaded, fake_client, clock):
        await loaded.resolve("unknown-1")
        clock.advance(300)
        await loaded.resolve("unknown-2")

        assert fake_client.call_count("fetch_versions") == 2

    async def test_concurrent_misses_trigger_once(self, loaded, fake_client):
        await asyncio.gather(*(loaded.resolve(f"unknown-{i}") for i in range(5)))

        assert fake_client.call_count("fetch_versions") == 1

    async def test_refresh_failure_returns_none(self, loaded, fake_client):
        fake_client.errors["fetch_versions"] = RuntimeError("down")

        assert await loaded.resolve("unknown-id") is None
        assert loaded.get_by_id(PRIMED_CONTINUITY_ID) is not None


class TestPeriodicRefresh:
    async def test_checks_version_periodically(self, make_catalog, fake_client):
        catalog = make_catalog(fake_client, refresh_interval=0.01)

        catalog.start_periodic_refresh()
        await asyncio.sleep(0.05)
        await catalog.stop_periodic_refresh()

        assert fake_client.call_count("fetch_versions") >= 2
        assert fake_client.call_count("fetch_items") == 2

    async def test_keeps_running_after_errors(self, make_catalog, fake_client):
        fake_client.errors["fetch_versions"] = RuntimeError("down")
        catalog = make_catalog(fake_client, refresh_interval=0.01)

        catalog.start_periodic_refresh()
        await asyncio.sleep(0.05)
        await catalog.stop_periodic_refresh()

        assert fake_client.call_count("fetch_versions") >= 2

    async def test_start_twice_runs_single_task(self, make_catalog):
        catalog = make_catalog(refresh_interval=10)

        catalog.start_periodic_refresh()
        first = catalog._refresh_task
        catalog.start_periodic_refresh()

        assert catalog._refresh_task is first
        await catalog.stop_periodic_refresh()
        assert catalog._refresh_task is None

    async def test_stop_without_start_is_noop(self, make_catalog):
        await make_catalog().stop_periodic_refresh()
