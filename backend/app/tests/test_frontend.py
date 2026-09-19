import pytest


def test_built_ui_routes_and_api_share_one_origin(client):
    from app.main import frontend_dist
    if not frontend_dist.is_dir():
        pytest.skip("Build frontend before testing static routes")
    for path in ("/", "/create", "/join", "/app", "/app/chat"):
        response = client.get(path)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert '<div id="root">' in response.text
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/api/does-not-exist").status_code == 404
