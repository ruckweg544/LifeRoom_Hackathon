def _create_household_with_members(client):
    owner = client.post(
        "/api/households",
        json={"display_name": "Seongjin", "household_name": "Foxridge House", "password": None},
    ).json()
    code = owner["household"]["room_code"]

    alex = client.post(
        "/api/households/join", json={"display_name": "Alex", "room_code": code}
    ).json()
    jamie = client.post(
        "/api/households/join", json={"display_name": "Jamie", "room_code": code}
    ).json()
    return owner, alex, jamie


def test_bill_split_equally_among_three(client):
    owner, alex, jamie = _create_household_with_members(client)
    token = owner["session_token"]

    resp = client.post(
        "/api/bills",
        json={
            "title": "Internet",
            "amount": 90.00,
            "paid_by_id": alex["member"]["id"],
            "participant_ids": [owner["member"]["id"], alex["member"]["id"], jamie["member"]["id"]],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    bill = resp.json()
    assert bill["amount_cents"] == 9000
    shares = sorted(p["share_cents"] for p in bill["participants"])
    assert shares == [3000, 3000, 3000]
    assert sum(shares) == 9000

    # Payer's own participant row should be auto-settled.
    payer_participant = next(p for p in bill["participants"] if p["member_id"] == alex["member"]["id"])
    assert payer_participant["settled"] is True


def test_bill_split_with_remainder_cents(client):
    owner, alex, jamie = _create_household_with_members(client)
    token = owner["session_token"]

    resp = client.post(
        "/api/bills",
        json={
            "title": "Groceries run",
            "amount": 10.00,
            "paid_by_id": owner["member"]["id"],
            "participant_ids": [owner["member"]["id"], alex["member"]["id"], jamie["member"]["id"]],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    bill = resp.json()
    shares = sorted((p["share_cents"] for p in bill["participants"]), reverse=True)
    # 1000 cents / 3 = 333.33 -> [334, 333, 333], summing exactly to 1000.
    assert shares == [334, 333, 333]
    assert sum(shares) == 1000


def test_negative_amount_rejected(client):
    owner, alex, jamie = _create_household_with_members(client)
    token = owner["session_token"]

    resp = client.post(
        "/api/bills",
        json={
            "title": "Bad bill",
            "amount": -5.0,
            "paid_by_id": owner["member"]["id"],
            "participant_ids": [owner["member"]["id"]],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
