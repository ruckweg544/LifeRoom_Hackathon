"""Verifies household isolation: no request can read or write another household's data."""


def _create_household(client, display_name="Seongjin", household_name="Foxridge House", password=None):
    resp = client.post(
        "/api/households",
        json={"display_name": display_name, "household_name": household_name, "password": password},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_household_returns_session_token(client):
    data = _create_household(client)
    assert data["session_token"]
    assert data["household"]["room_code"]
    assert len(data["household"]["room_code"]) == 6


def test_join_household_wrong_code_404(client):
    resp = client.post("/api/households/join", json={"display_name": "Alex", "room_code": "ZZZZZZ"})
    assert resp.status_code == 404


def test_join_household_wrong_password_401(client):
    _create_household(client, password="secret123")
    # Need the actual room code - fetch it via a second create then use that code.
    created = _create_household(client, household_name="Locked House", password="secret123")
    code = created["household"]["room_code"]

    resp = client.post(
        "/api/households/join",
        json={"display_name": "Alex", "room_code": code, "password": "wrong-password"},
    )
    assert resp.status_code == 401


def test_no_token_returns_401(client):
    resp = client.get("/api/chores")
    assert resp.status_code == 401


def test_cross_household_chore_is_not_visible(client):
    household_a = _create_household(client, display_name="A-Owner", household_name="House A")
    household_b = _create_household(client, display_name="B-Owner", household_name="House B")

    token_a = household_a["session_token"]
    token_b = household_b["session_token"]

    resp = client.post(
        "/api/chores",
        json={"title": "Household A chore", "priority": "medium"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 201
    chore_id = resp.json()["id"]

    # Household B should see zero chores - never household A's.
    resp_b = client.get("/api/chores", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b.status_code == 200
    assert resp_b.json() == []

    # Household B cannot fetch/modify household A's chore by ID either.
    resp_delete = client.delete(f"/api/chores/{chore_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_delete.status_code == 404


def test_cross_household_bill_participant_must_belong_to_same_household(client):
    household_a = _create_household(client, display_name="A-Owner", household_name="House A")
    household_b = _create_household(client, display_name="B-Owner", household_name="House B")

    token_a = household_a["session_token"]
    b_member_id = household_b["member"]["id"]

    resp = client.post(
        "/api/bills",
        json={
            "title": "Sneaky bill",
            "amount": 30.0,
            "paid_by_id": household_a["member"]["id"],
            "participant_ids": [household_a["member"]["id"], b_member_id],
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 400
