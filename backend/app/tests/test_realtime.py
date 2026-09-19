import hashlib

import pytest
from starlette.websockets import WebSocketDisconnect


def household(client, name="Alice"):
    response = client.post("/api/households", json={"display_name": name, "household_name": name + " house"})
    assert response.status_code == 201
    return response.json()


def headers(session):
    return {"Authorization": "Bearer " + session["session_token"]}


def event(socket, expected):
    # Presence events may precede the write notification.
    for _ in range(10):
        value = socket.receive_json()
        if value["type"] == "presence":
            continue
        assert value["type"] == expected, value
        return
    pytest.fail("Missing room event")


def test_two_clients_persistence_reconnect_and_isolation(client):
    alice = household(client)
    bob = client.post("/api/households/join", json={"display_name": "Bob", "room_code": alice["household"]["room_code"]}).json()
    other = household(client, "Outsider")
    path = "/ws/" + alice["household"]["id"]
    a, b = headers(alice), headers(bob)
    with client.websocket_connect(path) as first, client.websocket_connect(path) as second:
        first.send_json({"token": alice["session_token"]})
        event(first, "ready")
        second.send_json({"token": bob["session_token"]})
        event(second, "ready")
        message = client.post("/api/messages", headers=a, json={"content": "Hello Bob"})
        assert message.status_code == 201
        event(first, "message.created")
        event(second, "message.created")
        assert client.get("/api/messages", headers=b).json() == [message.json()]
        chore = client.post("/api/chores", headers=a, json={"title": "Dishes", "assigned_to_id": bob["member"]["id"]}).json()
        event(first, "household.changed")
        event(second, "household.changed")
        response = client.patch("/api/chores/" + chore["id"], headers=b, json={"completed": True})
        assert response.status_code == 200
        event(first, "household.changed")
        event(second, "household.changed")
        assert client.get("/api/chores", headers=a).json()[0]["completed"] is True
        bill = client.post("/api/bills", headers=a, json={"title": "Food", "amount": "10.01", "paid_by_id": alice["member"]["id"], "participant_ids": [alice["member"]["id"], bob["member"]["id"]]})
        assert bill.status_code == 201
        event(first, "household.changed")
        event(second, "household.changed")
        assert sum(p["share_cents"] for p in bill.json()["participants"]) == 1001
        assert client.get("/api/bills", headers=b).json() == [bill.json()]
        assert client.get("/api/messages", headers=headers(other)).json() == []
        assert client.patch("/api/chores/" + chore["id"], headers=headers(other), json={"completed": False}).status_code == 404
        assert client.patch("/api/chores/" + chore["id"], headers=a, json={"assigned_to_id": other["member"]["id"]}).status_code == 400

    # Writes missed while disconnected are recovered through REST after ready.
    client.post("/api/messages", headers=a, json={"content": "While offline"})
    with client.websocket_connect(path) as recovered:
        recovered.send_json({"token": bob["session_token"]})
        event(recovered, "ready")
        assert len(client.get("/api/messages", headers=b).json()) == 2
        assert len(client.get("/api/bills", headers=b).json()) == 1
    for token in (other["session_token"], "invalid"):
        with client.websocket_connect(path) as denied:
            denied.send_json({"token": token})
            with pytest.raises(WebSocketDisconnect) as error:
                denied.receive_json()
            assert error.value.code == 1008
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(path, headers={"origin": "https://untrusted.example"}):
            pass


def test_multiple_tabs_keep_member_online(client):
    alice = household(client)
    path = "/ws/" + alice["household"]["id"]
    with client.websocket_connect(path) as first:
        first.send_json({"token": alice["session_token"]})
        event(first, "ready")
        with client.websocket_connect(path) as second:
            second.send_json({"token": alice["session_token"]})
            event(second, "ready")
            assert client.get("/api/dashboard", headers=headers(alice)).json()["summary"]["members_online"] == 1
        assert client.get("/api/members", headers=headers(alice)).json()[0]["online"] is True
    assert client.get("/api/members", headers=headers(alice)).json()[0]["online"] is False


def test_validation_and_hashed_credentials(client):
    alice = household(client)
    a = headers(alice)
    from app.database.session import SessionLocal
    from app.models.member import Member
    with SessionLocal() as db:
        member = db.get(Member, alice["member"]["id"])
        assert member.session_token == hashlib.sha256(alice["session_token"].encode()).hexdigest()
        assert client.get("/api/members", headers={"Authorization": "Bearer " + member.session_token}).status_code == 401
    assert client.get("/api/households/me", headers=a).json()["session_token"] == alice["session_token"]
    chore = client.post("/api/chores", headers=a, json={"title": "Clean"}).json()
    for invalid in ({"completed": None}, {"title": "  "}, {"priority": None}):
        assert client.patch("/api/chores/" + chore["id"], headers=a, json=invalid).status_code == 422
    for invalid_amount in ("0.001", "NaN", "Infinity", "0", "-1"):
        assert client.post("/api/bills", headers=a, json={"title": "Bad", "amount": invalid_amount, "paid_by_id": alice["member"]["id"], "participant_ids": [alice["member"]["id"]]}).status_code == 422
    assert client.post("/api/households", json={"display_name":"A", "household_name":"Locked", "password":"가" * 30}).status_code == 422


def test_household_events_do_not_leak(client):
    alice, other = household(client), household(client, "Other")
    with client.websocket_connect("/ws/" + other["household"]["id"]) as socket:
        socket.send_json({"token":other["session_token"]})
        event(socket,"ready")
        client.post("/api/chores", headers=headers(alice), json={"title":"Private chore"})
        client.post("/api/messages", headers=headers(other), json={"content":"Own message"})
        event(socket,"message.created")
