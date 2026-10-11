import pytest

from main import app

PREFIX = "/api/v1/market"


def test_exposes_only_expected_routes():
    routes = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
    }

    assert routes == {
        ("GET", "/"),
        ("GET", f"{PREFIX}/users/{{username}}/orders"),
        ("GET", f"{PREFIX}/me/orders"),
        ("GET", f"{PREFIX}/items/{{slug}}/price"),
        ("GET", f"{PREFIX}/groups"),
        ("GET", f"{PREFIX}/groups/{{group_id}}/items"),
    }


@pytest.mark.parametrize(
    ("method", "path", "status_code"),
    [
        ("GET", f"{PREFIX}/items?category=baro", 404),
        ("PATCH", f"{PREFIX}/items/baro_01/price", 405),
        ("PATCH", f"{PREFIX}/items/baro_01/visibility", 404),
    ],
)
def test_legacy_mock_routes_are_removed(api_client, method, path, status_code):
    client = api_client()

    response = client.request(method, path, json={})

    assert response.status_code == status_code
