import pytest

from app.application.group_service import GroupService
from tests.support import StaticGroupRepository, make_group

GROUPS_URL = "/api/v1/market/groups"


@pytest.fixture
def group_service(loaded_catalog) -> GroupService:
    groups = [
        make_group("mods", "primed_continuity", "no_such_item"),
        make_group("empty"),
    ]
    return GroupService(StaticGroupRepository(groups), loaded_catalog)


def test_lists_groups(api_client, group_service):
    client = api_client(group_service=group_service)

    response = client.get(GROUPS_URL)

    assert response.status_code == 200
    assert response.json()["data"] == [
        {
            "id": "mods",
            "names": {"en": "Mods", "zh_hant": "mods 繁", "zh_hans": None},
            "item_count": 2,
        },
        {
            "id": "empty",
            "names": {"en": "Empty", "zh_hant": "empty 繁", "zh_hans": None},
            "item_count": 0,
        },
    ]


def test_lists_group_items(api_client, group_service):
    client = api_client(group_service=group_service)

    response = client.get(f"{GROUPS_URL}/mods/items")

    assert response.status_code == 200
    [item] = response.json()["data"]
    assert item["slug"] == "primed_continuity"
    assert item["names"]["zh_hant"] == "持久力 Prime"
    assert item["image"].startswith("https://warframe.market/static/assets/")
    assert item["max_rank"] == 10
    assert "mod" in item["tags"]


def test_empty_group_returns_empty_list(api_client, group_service):
    client = api_client(group_service=group_service)

    response = client.get(f"{GROUPS_URL}/empty/items")

    assert response.json()["data"] == []


def test_unknown_group_returns_404(api_client, group_service):
    client = api_client(group_service=group_service)

    response = client.get(f"{GROUPS_URL}/nope/items")

    assert response.status_code == 404
    assert response.json()["detail"] == "找不到分組: nope"


def test_app_serves_project_groups(api_client):
    client = api_client()

    response = client.get(GROUPS_URL)

    ids = [group["id"] for group in response.json()["data"]]
    assert "baro_ki_teer" in ids
    assert "steel_meridian" in ids
