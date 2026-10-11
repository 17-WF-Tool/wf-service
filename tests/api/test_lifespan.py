from fastapi.testclient import TestClient

from main import app

PRIMED_CONTINUITY_ID = "54c6855ee779891362942572"


def test_startup_warms_up_catalog_and_shutdown_stops_refresh(app_catalog):
    assert not app_catalog.is_loaded

    with TestClient(app):
        assert app_catalog.get_by_id(PRIMED_CONTINUITY_ID) is not None
        assert app_catalog._refresh_task is not None

    assert app_catalog._refresh_task is None
