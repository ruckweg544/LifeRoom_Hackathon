def _create_household(client):
    resp = client.post(
        "/api/households",
        json={"display_name": "Seongjin", "household_name": "Foxridge House", "password": None},
    )
    return resp.json()


def test_create_chore_requires_title(client):
    session = _create_household(client)
    token = session["session_token"]

    resp = client.post("/api/chores", json={"title": ""}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422


def test_create_and_complete_chore(client):
    session = _create_household(client)
    token = session["session_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = client.post(
        "/api/chores",
        json={"title": "Take out trash", "priority": "high"},
        headers=headers,
    )
    assert create_resp.status_code == 201
    chore = create_resp.json()
    assert chore["completed"] is False
    assert chore["priority"] == "high"

    complete_resp = client.patch(
        f"/api/chores/{chore['id']}", json={"completed": True}, headers=headers
    )
    assert complete_resp.status_code == 200
    completed = complete_resp.json()
    assert completed["completed"] is True
    assert completed["completed_at"] is not None


def test_chore_assignee_must_be_household_member(client):
    session = _create_household(client)
    token = session["session_token"]

    resp = client.post(
        "/api/chores",
        json={"title": "Clean kitchen", "assigned_to_id": "not-a-real-member-id"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_delete_chore(client):
    session = _create_household(client)
    token = session["session_token"]
    headers = {"Authorization": f"Bearer {token}"}

    chore = client.post("/api/chores", json={"title": "Vacuum"}, headers=headers).json()
    delete_resp = client.delete(f"/api/chores/{chore['id']}", headers=headers)
    assert delete_resp.status_code == 204

    list_resp = client.get("/api/chores", headers=headers)
    assert list_resp.json() == []
