import json
from datetime import datetime, timezone

import httpx
import pytest
from fastapi import HTTPException

from app.services import ai
from app.tests.test_realtime import household, headers


@pytest.fixture(autouse=True)
def reset_limits():
    ai._requests.clear()
    yield
    ai._requests.clear()


def test_analysis_access_mapping_and_confirmation(client, monkeypatch):
    alice = household(client)
    other = household(client, "Other")
    auth = headers(alice)
    message = client.post("/api/messages", headers=auth, json={"content": "Alice, dishes tomorrow"}).json()
    path = f"/api/messages/{message['id']}/analyze"
    calls = []

    async def detect(content, created_at):
        calls.append(content)
        return ai.TaskDetection(is_task=True, task_name="Do dishes", assignee="Alice", due_date="2026-09-20")

    monkeypatch.setattr(ai, "detect_task", detect)
    assert client.post(path).status_code == 401
    assert client.post(path, headers=headers(other)).status_code == 404
    assert calls == []
    response = client.post(path, headers=auth)
    assert response.status_code == 200
    suggestion = response.json()["suggestion"]
    assert suggestion["assigned_to_id"] == alice["member"]["id"]
    assert suggestion["due_date"] == "2026-09-20"
    assert client.get("/api/chores", headers=auth).json() == []
    payload = {"title": suggestion["title"], "source_message_id": message["id"]}
    assert client.post("/api/chores", headers=headers(other), json=payload).status_code == 404
    assert client.post("/api/chores", headers=auth, json=payload).status_code == 201
    assert client.post("/api/chores", headers=auth, json=payload).status_code == 409
    assert len(client.get("/api/chores", headers=auth).json()) == 1


@pytest.mark.parametrize("owner", ["Nobody", "Alice"])
def test_ambiguous_or_unknown_owner_unassigned(client, monkeypatch, owner):
    alice = household(client)
    joined = client.post("/api/households/join", json={"display_name": "Bob", "room_code": alice["household"]["room_code"]})
    assert joined.status_code == 200
    # Simulate ambiguous legacy names; normal joining rejects duplicate names.
    from app.database.session import SessionLocal
    from app.models.member import Member
    with SessionLocal() as db:
        db.get(Member, joined.json()["member"]["id"]).display_name = "Alice"
        db.commit()
    auth = headers(alice)
    message = client.post("/api/messages", headers=auth, json={"content": "설거지 부탁해"}).json()

    async def detect(*args):
        return ai.TaskDetection(is_task=True, task_name="설거지", assignee=owner)

    monkeypatch.setattr(ai, "detect_task", detect)
    result = client.post(f"/api/messages/{message['id']}/analyze", headers=auth).json()
    assert result["suggestion"]["assigned_to_id"] is None


def test_failure_is_not_small_talk_and_chat_survives(client, monkeypatch):
    auth = headers(household(client))
    message = client.post("/api/messages", headers=auth, json={"content": "Hello"}).json()
    path = f"/api/messages/{message['id']}/analyze"

    async def failure(*args):
        raise HTTPException(503, detail={"code": "AI_UNAVAILABLE"})

    monkeypatch.setattr(ai, "detect_task", failure)
    assert client.post(path, headers=auth).status_code == 503
    assert client.get("/api/messages", headers=auth).json() == [message]

    async def small_talk(*args):
        return ai.TaskDetection(is_task=False)

    monkeypatch.setattr(ai, "detect_task", small_talk)
    assert client.post(path, headers=auth).json()["suggestion"] is None
    for _ in range(8):
        assert client.post(path, headers=auth).status_code == 200
    assert client.post(path, headers=auth).status_code == 429


@pytest.mark.parametrize("result", ["valid", "invalid_date", "blank_title", "503", "timeout", "blocked"])
def test_gemini_transport_and_validation(monkeypatch, result):
    import asyncio
    from app.core.config import Settings
    settings = Settings(gemini_api_key="test-only-key", gemini_model="test-model")
    monkeypatch.setattr(ai, "get_settings", lambda: settings)

    async def post(self, url, **kwargs):
        assert kwargs["headers"]["x-goog-api-key"] == "test-only-key"
        assert "2026-09-18" in kwargs["json"]["systemInstruction"]["parts"][0]["text"]
        assert "responseJsonSchema" in kwargs["json"]["generationConfig"]
        if result == "timeout":
            raise httpx.ReadTimeout("timeout")
        task = {"is_task": True, "task_name": "Dishes", "due_date": "2026-09-20"}
        if result == "invalid_date":
            task["due_date"] = "not-a-date"
        if result == "blank_title":
            task["task_name"] = "   "
        body = {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(task)}]}}]}
        if result == "blocked":
            body = {"candidates": []}
        return httpx.Response(503 if result == "503" else 200, json=body, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    call = ai.detect_task("Dishes tomorrow", datetime(2026, 9, 19, 1, tzinfo=timezone.utc))
    if result == "valid":
        assert asyncio.run(call).task_name == "Dishes"
    else:
        with pytest.raises(HTTPException) as error:
            asyncio.run(call)
        assert error.value.status_code == 503
    assert ai._inflight == 0


def test_existing_database_migration(tmp_path, monkeypatch):
    from sqlalchemy import create_engine, inspect, text
    from app.database import session
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE chores (id VARCHAR(36) PRIMARY KEY, title VARCHAR(120))"))
        connection.execute(text("INSERT INTO chores VALUES ('existing', 'Keep me')"))
    monkeypatch.setattr(session, "engine", engine)
    session.init_db()
    session.init_db()
    assert "source_message_id" in {c["name"] for c in inspect(engine).get_columns("chores")}
    with engine.connect() as connection:
        assert connection.execute(text("SELECT title FROM chores")).scalar() == "Keep me"
        connection.execute(text("INSERT INTO chores VALUES ('one', 'A', 'message')"))
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            connection.execute(text("INSERT INTO chores VALUES ('two', 'B', 'message')"))
