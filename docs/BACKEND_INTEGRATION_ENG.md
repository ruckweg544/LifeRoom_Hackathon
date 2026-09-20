# Backend Comparison and Integration Order

> This is a record of the comparison against the previous `origin/feature/backend`. The subsequently provided ZIP's modified integrated version is located in `backend/` and `frontend/`, and the current execution method is described in [README](../README.md).
> The incomplete items below are based on the branch at that time and do not represent the current state of the integrated version.

Comparison basis: the locally stored `origin/feature/backend` at `41f0d9e`.
The remote repository was not fetched again, so commits after that point are not included.
`main.py`, `database.py`, `ai_service.py`, `requirements.txt`, and `start.sh` were reviewed.
The branch was neither merged nor modified.

## Parts That Cannot Be Connected Directly Yet

| Item | Backend | Data + Realtime |
| --- | --- | --- |
| Server | `main:app` | `app:app` |
| DB | Fixed path `app.db` | Environment variable `LIFEROOM_DB_PATH` |
| User | Per-room name, integer ID, no authentication | UUID, bearer session, membership check |
| Room | `rooms`, public `room_code`, automatically created on lookup | `households`, UUID, private invite code for joining |
| Join | `POST /api/join` | `POST /sessions`, `/households`, `/households/join` |
| State | `/api/rooms/{room_code}/state` | `/households/{id}/state` |
| Message author | Trusts the `sender` string from the request | `sender_id` determined from the token |
| Chore assignee | Name `assignee` | Member ID `assignee_id` |
| Chore completion | `/api/chores/{id}/complete?room_code=...` | `/households/{id}/chores/{id}`, with explicit `completed` |
| WebSocket | `/ws/{room_code}`, no authentication | `/households/{id}/events`, authentication in the first frame |
| Events | `new_message`, `new_chore`, `chore_completed` + object | `message.created`, `chore.created`, `chore.updated` + ID |
| Additional state | `rent_due_date`, `rent_amount`, chore `source` | `members`, `bills`, `balances_cents` |

The table names `users`, `messages`, and `chores` overlap, but their columns and ID types are different.
**Pointing both apps to the same DB file does not integrate them.** If existing data needs to be preserved, an explicit migration including ID mapping and name-to-member mapping is required.

## Priority

1. **Unify around a single server, DB, and user contract.** Keep the membership checks,
   UUIDs, and integer cents that have already been validated in the demo. Connect the Backend's
   AI functionality to this data path, and align the frontend request paths and token handling
   at the same time. Running two independent apps on the same port or simply changing API
   paths will not solve the integration.

2. **Strengthen the Backend's room boundary.** `database.complete_chore(chore_id)` currently
   modifies a chore without a room condition, while `main.complete_chore` sends the event
   using the request's `room_code`. It should verify the authenticated member, update using
   `WHERE id=? AND room_id=?`, and then send the notification to the same room. The current
   Data + Realtime path already performs this check.

3. **Choose a single frontend event-consumption strategy.** Under the current contract, the
   frontend can re-fetch `/state` on `ready` and on change events. Mixing this with the existing
   code that directly inserts `new_message` objects can cause missing or duplicate data.
   Re-read the snapshot after reconnecting as well.

4. **Connect AI through the same storage and notification path.** The Backend currently stores
   AI results directly with `db.add_chore`, so the other app's socket does not receive a
   notification. In the integrated server, reuse the verified chore-creation path. Do not
   execute synchronous Gemini calls directly inside async message handling; move them to a
   thread so socket processing is not blocked. If only a name is returned for the assignee and
   it cannot be resolved to a member ID, leave the chore unassigned.

5. **Resolve Backend execution issues.** `main.py` expects a `../frontend` directory, which is
   not present in the compared branch, causing the static-file mount to fail. Also, because
   `load_dotenv()` is called after importing `ai_service`, an API key that exists only in
   `.env` is not applied during AI initialization. Environment loading should occur before
   importing the AI module.

## Minimal Changes Applied This Time

- Changed `/state` so that bill shares are retrieved with a single JOIN instead of querying
  shares separately for each bill. For N bills, the number of share queries is reduced from
  N to 1, while keeping the response contract unchanged.
- Added regression tests covering shares/balances for multiple bills and single-item retrieval.
- Updated the current branch's `.gitignore` to prevent locally generated Backend artifacts such
  as `venv/`, `.env`, and `app.db` from being reintroduced. Files that are already tracked in
  another branch are not removed by `.gitignore` alone. The contents of `.env` were not opened,
  and if actual keys were committed, the responsible person should rotate the keys and separately
  clean up the tracked files.

Backend's `get_messages` returns only the oldest 100 messages, so recent messages may be omitted.
If that path is retained, use `ORDER BY id DESC LIMIT ?` to retrieve the most recent messages and
then reverse their display order. The current `/state` endpoint can continue returning all messages
for demo-scale data; pagination and a separate message retrieval API can be added when actual data
volume requires them.

The Backend and execution environment are not yet fully integrated. The contract integration and
Backend modifications described above are still pending.
"""

path = Path("/mnt/data/backend_comparison_integration_order.md")
path.write_text(content, encoding="utf-8")
print(path)
