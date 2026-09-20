"""Check that the local demo scenarios exercise the real analysis API."""
import importlib.util
from pathlib import Path

from app.services import ai
from app.tests.test_realtime import household, headers


def test_local_demo_scenarios(client, monkeypatch):
    path = Path(__file__).resolve().parents[3] / "scripts" / "test_server.py"
    spec = importlib.util.spec_from_file_location("demo", path)
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    monkeypatch.setattr(ai, "detect_task", demo.fake_detection)
    ai._requests.clear()
    auth = headers(household(client))
    for content, expected, code in [
        ("[task] Do dishes", 200, None),
        ("[quota] test", 503, "AI_PROVIDER_RATE_LIMITED"),
        ("[error] test", 503, "AI_UNAVAILABLE"),
        ("ㅋㅋㅋ", 200, None),
    ]:
        message = client.post("/api/messages", headers=auth, json={"content": content}).json()
        url = f"/api/messages/{message['id']}/analyze"
        response = client.post(url, headers=auth)
        assert response.status_code == expected
        if code:
            assert response.json()["detail"]["code"] == code
        else:
            assert response.json()["is_task"] == content.startswith("[task]")
        assert client.post(url, headers=auth).json() == response.json()
    assert client.get("/api/chores", headers=auth).json() == []
    ai._requests.clear()
