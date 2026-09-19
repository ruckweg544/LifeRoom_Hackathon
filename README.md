# LifeRoom — Data + Realtime

Minimal FastAPI + SQLite service for the household demo. The repository had no
application code when this service was added. React, production authentication,
and Gemini remain integration points owned by the other teammates.

## Run

Requires Python 3.11+.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000 --workers 1
```

Interactive REST documentation: http://127.0.0.1:8000/docs

Environment variables (see `.env.example`; the application does not automatically
load `.env`):

- `LIFEROOM_DB_PATH`: SQLite file, default `data/liferoom.sqlite3`.
- `LIFEROOM_ALLOWED_ORIGINS`: comma-separated frontend origins, default
  `http://localhost:5173,http://127.0.0.1:5173`. Used for CORS and WebSocket origin checks.

The schema is initialized on startup. Store the database directory on persistent
storage when hosting. Use **one worker**: socket subscriptions live in memory.
SQLite and full household snapshots are intentionally sized for a small demo.
Use HTTPS/WSS outside localhost.

## Identity and households

`POST /sessions` with `{"name":"Alice"}` creates a guest identity and returns
`{"user":{"id":"...","name":"Alice"},"token":"..."}`. Save the token privately;
subsequent REST requests require `Authorization: Bearer <token>`. Display names
are not identities. Tokens and invite codes are generated randomly; only their
hashes are stored in SQLite. No configured secret is required.

This is demo guest authentication: no passwords, account recovery, session expiry,
or revocation. The backend team should replace session issuance/verification with
its chosen authentication while preserving user IDs and membership checks. Do not
expose this guest bootstrap publicly as finished production authentication.

1. Alice creates a household with `POST /households`, body `{"name":"Our house"}`.
   Response includes `id`, `name`, and a private `invite_code` shown only at creation.
2. Bob creates his own session, then calls `POST /households/join` with
   `{"invite_code":"<Alice's invite>"}`. Rejoining is idempotent.
3. `GET /households` returns the caller's households. Each household member can
   read and update household data. Nonmembers are rejected, including on sockets.

## REST contract

All paths below start with `/households/{household_id}` and require a bearer token.
IDs are strings. Dates are `YYYY-MM-DD`; timestamps are UTC. Responses use the
same field names as requests, plus persisted IDs and ownership fields.

| Method/path | Request | Result |
| --- | --- | --- |
| `GET /state` | — | Household snapshot: `members`, `messages`, `chores`, `bills`, `balances_cents` |
| `POST /messages` | `{"content":"Hello!"}` | Saved message with `id`, `household_id`, `sender_id`, `content`, `created_at` |
| `POST /chores` | `{"title":"Dishes","assignee_id":"<member ID>","due_date":"2026-09-20"}` | Saved chore; `completed` starts as `false` |
| `PATCH /chores/{chore_id}` | `{"completed":true}` | Updated chore; also accepts `assignee_id` and `due_date` |
| `POST /bills` | `{"title":"Groceries","amount_cents":1001,"payer_id":"<member ID>","participant_ids":["<Alice ID>","<Bob ID>"]}` | Saved bill with exact `shares` |

Chore assignment and due date are optional; send `null` in a patch to clear them.
Completion must be a boolean and is set explicitly, never toggled. Concurrent
updates to the same field use last-write-wins; unrelated patch fields are preserved.

Bills split equally across the selected participants. Remainder cents go to
participants in sorted user-ID order. Payer and participants must be household
members; participants must be unique. Bills and shares commit atomically.
Amounts use integer cents in one household currency (USD for this demo).
Positive `balances_cents[user_id]` means the member is owed money; negative means
they owe money. Balances are derived from saved bills, not separately maintained.

## WebSocket contract

Connect to `ws://127.0.0.1:8000/households/{household_id}/events`.
Send `{"token":"<session token>"}` as the first frame within five seconds.
Tokens are deliberately excluded from URLs. Invalid authentication, membership,
or browser origins are rejected. Server-side ping/pong is handled by Uvicorn.

The server replies with `{"type":"ready","household_id":"..."}`. After that,
each committed mutation notifies every connected household member, including
its sender:

```json
{"type":"chore.updated","household_id":"...","entity_id":"..."}
```

Event types: `member.joined`, `message.created`, `chore.created`, `chore.updated`,
and `bill.created`. Frames after authentication are not mutation commands; use
REST to create messages and change data. An event invalidates the snapshot; it
does not carry an independently mergeable copy of an entity.

Frontend integration:

1. Register the socket message handler, connect, and send the token on open.
2. On `ready` **and every event**, fetch `/state` and replace the displayed state.
   Serialize refresh requests; if an event arrives during a fetch, fetch again
   afterward. This avoids an older response overwriting newer state.
3. On socket close, reconnect with a capped retry delay; authenticate and fetch
   again after `ready`. Stop retrying on authentication rejection (`1008`).
4. Close the socket when leaving the household or unmounting the UI.
5. Handle REST errors visibly and refresh after successful writes as well.

Notifications are not durable or replayed. Persisted snapshots recover missed
events after reconnects or server restarts. Subscribe before the initial fetch
so writes between loading and subscription are not missed. Slow/disconnected
sockets are removed without undoing committed writes. Avoid automatic retries
of POST requests after ambiguous network failures: create operations do not yet
accept idempotency keys.

## Verify the demo

```sh
source .venv/bin/activate
python -m unittest -v test_app
```

The integration check uses a temporary database and two authenticated WebSocket
clients. It verifies joining, chat delivery, chore creation/completion, equal bill
splits and balances, reconnect snapshots, persistence across application restarts,
input validation, and rejection of nonmembers and untrusted browser origins.
It does not require or modify a running server or a real household database.

For a frontend demo, open two browser sessions with separate guest identities,
join the same household, and wire both to the socket/REST contract above.
There is no React UI in this repository yet. Receipt processing, recurring bills,
and AI features are outside this Data + Realtime demo slice.

Implementation references: [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
and [lifespan testing](https://fastapi.tiangolo.com/advanced/testing-events/).
