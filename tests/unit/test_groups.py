import json
import logging

import pytest

from app.adapters.outbound.json_group_repository import JsonGroupRepository
from app.application.catalog_service import CatalogService
from app.application.group_service import GroupService
from app.config import settings
from tests.support import FakeMarketClient, StaticGroupRepository, make_group


def write_groups(tmp_path, groups: list[dict]):
    path = tmp_path / "groups.json"
    path.write_text(json.dumps({"groups": groups}, ensure_ascii=False), "utf-8")
    return path


class TestJsonGroupRepository:
    def test_parses_groups_in_order(self, tmp_path):
        path = write_groups(
            tmp_path,
            [
                {
                    "id": "baro",
                    "names": {"en": "Baro", "zh_hant": "巴羅"},
                    "source": "manual",
                    "slugs": ["b", "a", "b"],
                },
                {"id": "loka", "names": {"en": "New Loka"}, "slugs": []},
            ],
        )

        groups = JsonGroupRepository(path).list_groups()

        assert [g.id for g in groups] == ["baro", "loka"]
        assert groups[0].names.zh_hant == "巴羅"
        assert groups[0].names.zh_hans is None
        assert groups[0].slugs == ("b", "a")

    def test_duplicate_id_raises(self, tmp_path):
        group = {"id": "baro", "names": {"en": "Baro"}, "slugs": []}
        path = write_groups(tmp_path, [group, group])

        with pytest.raises(ValueError, match="分組 id 重複: baro"):
            JsonGroupRepository(path)

    @pytest.mark.parametrize(
        "group",
        [
            {"names": {"en": "Baro"}},
            {"id": "baro"},
            {"id": "baro", "names": {"zh_hant": "巴羅"}},
        ],
    )
    def test_malformed_group_raises(self, tmp_path, group):
        path = write_groups(tmp_path, [group])

        with pytest.raises(ValueError, match="格式錯誤"):
            JsonGroupRepository(path)

    def test_project_groups_file_is_valid(self):
        groups = JsonGroupRepository(settings.GROUPS_FILE).list_groups()

        ids = [g.id for g in groups]
        assert "baro_ki_teer" in ids
        assert "steel_meridian" in ids
        for group in groups:
            assert group.slugs, group.id
            assert group.names.zh_hant, group.id
            assert group.names.zh_hans, group.id


class TestGroupService:
    @pytest.fixture
    def service(self, loaded_catalog) -> GroupService:
        groups = [
            make_group("mods", "primed_continuity", "no_such_item"),
            make_group("blueprints", "vadarya_prime_blueprint"),
        ]
        return GroupService(StaticGroupRepository(groups), loaded_catalog)

    def test_lists_groups(self, service):
        assert [g.id for g in service.list_groups()] == ["mods", "blueprints"]

    def test_get_group_items_skips_unknown_slugs(self, service):
        items = service.get_group_items("mods")

        assert [item.slug for item in items] == ["primed_continuity"]

    def test_unknown_group_raises_key_error(self, service):
        with pytest.raises(KeyError, match="找不到分組: nope"):
            service.get_group_items("nope")

    def test_find_unknown_slugs_logs_warning(self, service, caplog):
        with caplog.at_level(logging.WARNING):
            unknown = service.find_unknown_slugs()

        assert unknown == {"mods": ["no_such_item"]}
        assert "no_such_item" in caplog.text

    def test_find_unknown_slugs_skips_when_catalog_not_loaded(self, caplog):
        groups = [make_group("mods", "no_such_item")]
        service = GroupService(
            StaticGroupRepository(groups), CatalogService(FakeMarketClient())
        )

        with caplog.at_level(logging.WARNING):
            unknown = service.find_unknown_slugs()

        assert unknown == {}
        assert "略過分組 slug 檢查" in caplog.text
