import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app import create_app


class DemoTest(unittest.TestCase):
    def test_demo_persistence_and_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "demo.sqlite3"
            with TestClient(create_app(path)) as client:
                def session(name):
                    response = client.post("/sessions", json={"name": name})
                    self.assertEqual(response.status_code, 201)
                    data = response.json()
                    return data["user"]["id"], data["token"], {"Authorization": f"Bearer {data['token']}"}

                alice, alice_token, a = session("Alice")
                bob, bob_token, b = session("Bob")
                outsider, outsider_token, other = session("Outsider")
                response = client.post("/households", headers=a, json={"name": "Our house"})
                self.assertEqual(response.status_code, 201)
                house = response.json()
                root = f"/households/{house['id']}"
                with client.websocket_connect(root + "/events") as ws_a:
                    ws_a.send_json({"token": alice_token})
                    self.assertEqual(ws_a.receive_json()["type"], "ready")
                    response = client.post("/households/join", headers=b, json={"invite_code": house["invite_code"]})
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(ws_a.receive_json()["type"], "member.joined")
                    with client.websocket_connect(root + "/events") as ws_b:
                        ws_b.send_json({"token": bob_token})
                        self.assertEqual(ws_b.receive_json()["type"], "ready")

                        def event_on_both(event_type, entity_id):
                            expected = {"type": event_type, "household_id": house["id"], "entity_id": entity_id}
                            self.assertEqual(ws_a.receive_json(), expected)
                            self.assertEqual(ws_b.receive_json(), expected)

                        message = client.post(root + "/messages", headers=a, json={"content": "Hello Bob!"})
                        self.assertEqual(message.status_code, 201)
                        event_on_both("message.created", message.json()["id"])
                        self.assertEqual(client.get(root + "/state", headers=b).json()["messages"][0]["content"], "Hello Bob!")

                        chore = client.post(root + "/chores", headers=a, json={
                            "title": "Dishes", "assignee_id": bob, "due_date": "2026-09-20"})
                        self.assertEqual(chore.status_code, 201)
                        chore_id = chore.json()["id"]
                        event_on_both("chore.created", chore_id)
                        self.assertEqual(client.get(root + "/state", headers=b).json()["chores"][0]["assignee_id"], bob)
                        response = client.patch(root + "/chores/" + chore_id, headers=b, json={"completed": True})
                        self.assertEqual(response.status_code, 200)
                        event_on_both("chore.updated", chore_id)
                        self.assertIs(client.get(root + "/state", headers=a).json()["chores"][0]["completed"], True)

                        bill = client.post(root + "/bills", headers=a, json={
                            "title": "Groceries", "amount_cents": 1001, "payer_id": alice,
                            "participant_ids": [alice, bob]})
                        self.assertEqual(bill.status_code, 201)
                        event_on_both("bill.created", bill.json()["id"])
                        self.assertEqual(sum(s["amount_cents"] for s in bill.json()["shares"]), 1001)
                        snapshot = client.get(root + "/state", headers=b).json()
                        self.assertEqual(snapshot["bills"][0], bill.json())
                        self.assertEqual(sum(snapshot["balances_cents"].values()), 0)
                        bob_share = next(s["amount_cents"] for s in bill.json()["shares"] if s["user_id"] == bob)
                        self.assertEqual(snapshot["balances_cents"], {alice: bob_share, bob: -bob_share})

                # A new connection gets ready, then reads the full persisted snapshot.
                with client.websocket_connect(root + "/events") as reconnected:
                    reconnected.send_json({"token": bob_token})
                    self.assertEqual(reconnected.receive_json()["type"], "ready")
                    self.assertEqual(client.get(root + "/state", headers=b).json(), snapshot)

                self.assertEqual(client.get(root + "/state", headers=other).status_code, 403)
                self.assertEqual(client.post(root + "/messages", headers=other, json={"content": "Intrusion"}).status_code, 403)
                self.assertEqual(client.post(root + "/chores", headers=other, json={"title": "Intrusion"}).status_code, 403)
                self.assertEqual(client.patch(root + "/chores/" + chore_id, headers=other, json={"completed": False}).status_code, 403)
                with client.websocket_connect(root + "/events") as forbidden:
                    forbidden.send_json({"token": outsider_token})
                    with self.assertRaises(WebSocketDisconnect) as error:
                        forbidden.receive_json()
                    self.assertEqual(error.exception.code, 1008)
                with client.websocket_connect(root + "/events") as invalid:
                    invalid.send_json({"token": "invalid"})
                    with self.assertRaises(WebSocketDisconnect):
                        invalid.receive_json()
                with self.assertRaises(WebSocketDisconnect):
                    with client.websocket_connect(root + "/events", headers={"origin": "https://untrusted.example"}):
                        pass

                self.assertEqual(client.post(root + "/messages", headers=a, json={"content": "  "}).status_code, 422)
                self.assertEqual(client.post(root + "/chores", headers=a, json={"title": "Bad", "assignee_id": outsider}).status_code, 403)
                self.assertEqual(client.post(root + "/chores", headers=a, json={"title": "Bad", "due_date": "2026-02-30"}).status_code, 422)
                self.assertEqual(client.patch(root + "/chores/" + chore_id, headers=a, json={"completed": None}).status_code, 422)
                self.assertEqual(client.patch(root + "/chores/missing", headers=a, json={"completed": True}).status_code, 404)
                payload = {"title": "Bad bill", "amount_cents": 100, "payer_id": alice, "participant_ids": [alice, outsider]}
                self.assertEqual(client.post(root + "/bills", headers=a, json=payload).status_code, 403)
                payload["participant_ids"] = [alice, alice]
                self.assertEqual(client.post(root + "/bills", headers=a, json=payload).status_code, 422)
                payload["participant_ids"] = [alice, bob]
                for amount in (0, -1, 1.5, True):
                    payload["amount_cents"] = amount
                    self.assertEqual(client.post(root + "/bills", headers=a, json=payload).status_code, 422)
                self.assertEqual(client.get(root + "/state", headers=b).json(), snapshot)

                other_house = client.post("/households", headers=other, json={"name": "Other house"}).json()
                other_root = f"/households/{other_house['id']}"
                self.assertEqual(client.patch(other_root + "/chores/" + chore_id, headers=other,
                                              json={"completed": False}).status_code, 404)
                self.assertEqual(client.get(other_root + "/state", headers=other).json()["messages"], [])
                self.assertEqual(len(client.get("/households", headers=b).json()), 1)
                with client.websocket_connect(other_root + "/events") as other_socket:
                    other_socket.send_json({"token": outsider_token})
                    self.assertEqual(other_socket.receive_json()["type"], "ready")
                    # An event in Alice's household must not reach this socket.
                    client.post(root + "/messages", headers=a, json={"content": "Private"})
                    own_message = client.post(other_root + "/messages", headers=other, json={"content": "Other room"}).json()
                    self.assertEqual(other_socket.receive_json()["entity_id"], own_message["id"])
                cleared = client.patch(root + "/chores/" + chore_id, headers=a,
                                       json={"assignee_id": None, "due_date": None}).json()
                self.assertIsNone(cleared["assignee_id"])
                self.assertIsNone(cleared["due_date"])
                self.assertIs(cleared["completed"], True)
                snapshot = client.get(root + "/state", headers=b).json()

            # Recreate the application against the same file: sessions and data survive.
            with TestClient(create_app(path)) as restarted:
                self.assertEqual(restarted.get(root + "/state", headers=b).json(), snapshot)


if __name__ == "__main__":
    unittest.main()
