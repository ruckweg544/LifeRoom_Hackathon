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
    assert client.post(path, headers=auth).json() == response.json()
    assert len(calls) == 1
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
    message = client.post("/api/messages", headers=auth, json={"content": "What time is dinner?"}).json()
    path = f"/api/messages/{message['id']}/analyze"

    async def failure(*args):
        raise HTTPException(503, detail={"code": "AI_UNAVAILABLE"})

    monkeypatch.setattr(ai, "detect_task", failure)
    assert client.post(path, headers=auth).status_code == 503
    assert client.get("/api/messages", headers=auth).json() == [message]

    async def small_talk(*args):
        return ai.TaskDetection(is_task=False)

    monkeypatch.setattr(ai, "detect_task", small_talk)
    # Failed provider attempts are terminal, even after the provider recovers.
    assert client.post(path, headers=auth).status_code == 503
    for _ in range(9):
        fresh = client.post("/api/messages", headers=auth, json={"content": "What time is dinner?"}).json()
        assert client.post(f"/api/messages/{fresh['id']}/analyze", headers=auth).status_code == 200
    fresh = client.post("/api/messages", headers=auth, json={"content": "Water plants"}).json()
    response = client.post(f"/api/messages/{fresh['id']}/analyze", headers=auth)
    assert response.status_code == 429
    assert response.json()["detail"]["code"] == "AI_RATE_LIMITED"
    ai._requests.clear()
    assert client.post(f"/api/messages/{fresh['id']}/analyze", headers=auth).status_code == 200


@pytest.mark.parametrize("result", ["valid", "invalid_date", "blank_title", "503", "429", "timeout", "blocked"])
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
        return httpx.Response(int(result) if result in ("503", "429") else 200, json=body, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    call = ai.detect_task("Dishes tomorrow", datetime(2026, 9, 19, 1, tzinfo=timezone.utc))
    if result == "valid":
        assert asyncio.run(call).task_name == "Dishes"
    else:
        with pytest.raises(HTTPException) as error:
            asyncio.run(call)
        assert error.value.status_code == 503
        assert error.value.detail["code"] == ("AI_PROVIDER_RATE_LIMITED" if result == "429" else "AI_UNAVAILABLE")
    assert ai._inflight == 0


def test_existing_database_migration(tmp_path, monkeypatch):
    from sqlalchemy import create_engine, inspect, text
    from app.database import session
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE messages (id VARCHAR(36) PRIMARY KEY)"))
        connection.execute(text("INSERT INTO messages VALUES ('old-chat')"))
        connection.execute(text("CREATE TABLE chores (id VARCHAR(36) PRIMARY KEY, title VARCHAR(120))"))
        connection.execute(text("INSERT INTO chores VALUES ('existing', 'Keep me')"))
    monkeypatch.setattr(session, "engine", engine)
    session.init_db()
    session.init_db()
    assert "source_message_id" in {c["name"] for c in inspect(engine).get_columns("chores")}
    with engine.connect() as connection:
        assert connection.execute(text("SELECT title FROM chores")).scalar() == "Keep me"
        assert connection.execute(text("SELECT analysis_status FROM messages WHERE id='old-chat'")).scalar() == "skipped"
        connection.execute(text("INSERT INTO chores VALUES ('one', 'A', 'message')"))
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            connection.execute(text("INSERT INTO chores VALUES ('two', 'B', 'message')"))


@pytest.mark.parametrize("content", ["Hello!!", "안녕하세요 👋", "ㅋㅋㅋ", "ㅎㅎㅎ", "ㅠㅠ", "👍🎉", "...", "THANK YOU!", "ㅇㅋ", "ㅇㅇ", "ㄴㄴ", "아ㅏㅏ", "ok", "okay", "thanks", "ㅋㅋ", "ㅎㅎ"])
def test_noise_skips_provider_and_quota(client, monkeypatch, content):
    auth = headers(household(client))
    message = client.post("/api/messages", headers=auth, json={"content": content}).json()

    def unexpected(*args):
        pytest.fail("Noise must not reserve quota or call Gemini")

    monkeypatch.setattr(ai, "reserve_analysis", unexpected)
    monkeypatch.setattr(ai, "detect_task", unexpected)
    result = client.post(f"/api/messages/{message['id']}/analyze", headers=auth)
    assert result.status_code == 200
    assert result.json() == {"message_id": message["id"], "is_task": False, "suggestion": None}
    assert client.get("/api/messages", headers=auth).json() == [message]


@pytest.mark.parametrize("content", ["설거지", "청소해", "trash?", "hi, clean the kitchen", "ㅋㅋ 내일까지 쓰레기 버려줘", "고마워, 설거지도 부탁해", "민수야 물 줘", "buy milk", "👍 do dishes", "what time is dinner?"])
def test_ambiguous_and_task_messages_are_not_filtered(content):
    assert not ai.is_obvious_noise(content)


@pytest.mark.parametrize("content", ["", "   ", "\n\t"])
def test_empty_noise_is_skipped(content):
    assert ai.is_obvious_noise(content)


@pytest.mark.parametrize("failure", [False, True])
def test_concurrent_analysis_claim_and_persisted_result(client, monkeypatch, failure):
    import asyncio
    import threading
    from concurrent.futures import ThreadPoolExecutor
    auth = headers(household(client))
    message = client.post("/api/messages", headers=auth, json={"content": "Please water plants"}).json()
    path = f"/api/messages/{message['id']}/analyze"
    entered, release = threading.Event(), threading.Event()
    calls = []

    async def detect(*args):
        calls.append(1)
        entered.set()
        await asyncio.to_thread(release.wait, 5)
        if failure:
            raise HTTPException(503, detail={"code": "AI_PROVIDER_RATE_LIMITED", "retryable": True})
        return ai.TaskDetection(is_task=True, task_name="Water plants")

    monkeypatch.setattr(ai, "detect_task", detect)
    with ThreadPoolExecutor() as pool:
        first = pool.submit(client.post, path, headers=auth)
        try:
            assert entered.wait(5)
            assert client.post(path, headers=auth).status_code == 409
        finally:
            release.set()
        result = first.result()
    # New DB sessions and cleared process quota cannot reset the persisted claim.
    ai._requests.clear()
    repeated = client.post(path, headers=auth)
    assert repeated.status_code == result.status_code == (503 if failure else 200)
    assert repeated.json() == result.json()
    assert len(calls) == 1
    if failure:
        assert result.json()["detail"] == {"code": "AI_PROVIDER_RATE_LIMITED", "retryable": False}
    assert client.get("/api/chores", headers=auth).json() == []


def test_skipped_status_survives_filter_changes(client, monkeypatch):
    from app.database.session import SessionLocal
    from app.models.message import Message
    auth = headers(household(client))
    message = client.post("/api/messages", headers=auth, json={"content": "ㅋㅋㅋ"}).json()
    path = f"/api/messages/{message['id']}/analyze"
    assert client.post(path, headers=auth).status_code == 200
    with SessionLocal() as db:
        assert db.get(Message, message["id"]).analysis_status == "skipped"
    monkeypatch.setattr(ai, "is_obvious_noise", lambda _: pytest.fail("Must reuse saved skip"))
    assert client.post(path, headers=auth).json()["is_task"] is False


@pytest.mark.parametrize("due_time, expected", [("21:00:00", "2026-09-20T21:00:00-04:00"), (None, None)])
def test_analysis_preserves_clock_time(client, monkeypatch, due_time, expected):
    auth = headers(household(client))
    message = client.post("/api/messages", headers=auth, json={"content": "Do dishes tomorrow at 9pm"}).json()
    async def detect(*args):
        return ai.TaskDetection(is_task=True, task_name="Dishes", due_date="2026-09-20", due_time=due_time)
    monkeypatch.setattr(ai, "detect_task", detect)
    response = client.post(f"/api/messages/{message['id']}/analyze", headers=auth)
    suggestion = response.json()["suggestion"]
    assert suggestion["due_at"] == expected
    chore = client.post('/api/chores', headers=auth, json={"title": "Dishes", "due_date": suggestion["due_at"]}).json()
    assert chore["due_date"] == ("2026-09-21T01:00:00Z" if due_time else None)
