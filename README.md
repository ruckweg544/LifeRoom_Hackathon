# LifeRoom

Roommate household demo: React + TypeScript + Vite frontend, FastAPI + SQLAlchemy
+ SQLite backend.

## Run the integrated app

Python 3.11+ and Node 22.12+ are required. From the repository root:

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

In another terminal:

```sh
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Open http://127.0.0.1:5173. API docs: http://127.0.0.1:8000/docs.
Create a household, copy its code from Members, and join with a different name in
another browser profile/private window. Those sessions can exchange messages,
create/assign/complete chores, and split bills with live updates. Separate profiles
are needed because the guest session is stored in localStorage.

Optional local settings are documented in each directory's `.env.example`.
The backend reads its `.env`; frontend `VITE_*` values are public configuration,
never secrets. Default database is `backend/liferoom.db` when started as above.
Use persistent storage and HTTPS/WSS when hosting. **Run one backend worker**;
connections and presence are process-local.

## Data and realtime contract

- `POST /api/households` and `/api/households/join` issue a random guest bearer
  token. Only its SHA-256 digest is stored. Passwords for joining are optional and
  bcrypt-hashed. Guest sessions have no expiration/recovery or revocation yet.
- All resource routes derive household membership from the bearer token.
  Assignees, payers, participants, reads and updates are checked against that room.
- Send messages through `POST /api/messages`. The sender comes from the session;
  the UI clears its draft only after the server confirms the saved message.
- Connect to `/ws/{household_id}`, then send `{"token":"..."}` within five seconds.
  Browser origins and room membership are checked. Tokens never appear in the URL.
- `ready`, `presence`, `message.created`, and `household.changed` trigger REST
  refreshes. Writes notify only after commit. Subscribe-before-refresh and a fresh
  read after reconnect recover missed events. Older requests cannot overwrite a
  newer page request. REST POST retries are manual (no idempotency keys yet).
- Bills accept decimal dollars with at most two fractional digits, store integer
  cents, and split remainder cents deterministically. Participant shares and bills
  commit together. Payer's own share cannot be marked unpaid.
- Presence is derived from active sockets, so closing one of several tabs does
  not incorrectly mark a member offline.

## Validation

```sh
cd backend
.venv/bin/python -m pytest -q
```

```sh
cd frontend
npm run build
npm run lint
```

The backend suite covers API access, password validation, money, two authenticated
WebSocket clients, room isolation, reconnect reads, multiple-tab presence, hashed
credentials and invalid updates. Frontend build checks TypeScript and all imports.

## Scope

The application lives in `backend/` and `frontend/`. The retired standalone server
and its schema/tests remain available in Git history; they are not needed to run
this app. Existing database files are not migrated or removed automatically.

AI, receipt scanning and monthly recurring expenses are not implemented.
Use the two-profile flow above for visual acceptance testing.


### Optional chat-to-chore analysis API

Set `GEMINI_API_KEY` and `GEMINI_MODEL` in the backend environment (choose a
model enabled for your Google project). `AI_TIMEZONE` defaults to
`America/New_York`. No new dependencies are required; analysis uses async HTTP.

1. Save chat with `POST /api/messages` as usual.
2. Call `POST /api/messages/{message_id}/analyze` with the same bearer token.
   Only messages in the caller's household can be analyzed.
3. Show the returned suggestion for confirmation. Analysis never creates a chore.
4. Submit the confirmed values to `POST /api/chores`, including
   `source_message_id: message_id`. A duplicate linked chore returns `409`.
   Existing `household.changed` notifications synchronize the result.

Example analysis response:
```json
{"message_id":"uuid","is_task":true,"suggestion":{"title":"Do dishes","assigned_to_id":null,"due_date":"2026-09-20"}}
```

Small talk returns `is_task: false, suggestion: null`. Provider failures return
`503` with `detail.code: AI_UNAVAILABLE`; missing configuration returns
`AI_NOT_CONFIGURED`. Retry analysis only, not message creation. Requests are
limited to 10 per household per minute and 4 simultaneous calls per process
(`429 AI_RATE_LIMITED`); these demo limits assume a single server worker.
Provider calls have a 15-second total timeout and no automatic retries.

Suggestion dates are calendar dates, resolved relative to the message timestamp
in `AI_TIMEZONE`. Explicit clock times are returned as `due_at`, an ISO datetime with an offset
in `AI_TIMEZONE`. The form converts it to device-local time and preserves the
instant when saving. Date-only suggestions leave time blank for user selection;
no default 18:00 is invented. Unknown or ambiguous assignees remain null.
Chat now analyzes newly sent messages and offers Review & add for detected chores.
Users can edit the title, assignee, and local due time before confirming. Analysis
failures offer Retry analysis for that message without resending chat. Analysis
starts only after a successful send; history loading, rerenders, and refreshes
do not trigger analysis. Suggestions are not persisted across page reloads.
Run `npm --prefix frontend test` for the React analysis-flow regression test.

On startup an additive migration adds the nullable `chores.source_message_id`
column and its unique index to existing databases. Existing chores are preserved;
back up the database before deployment. Deleting a chore permits recreating it
from the message. The AI route has mocked tests; live Gemini verification requires
your project's credentials/model.

Obvious greetings, acknowledgements, laughter and emoji-only messages are filtered
locally by the analysis endpoint before Gemini quota is reserved. They return the
normal `is_task: false` response. Ambiguous text and greetings mixed with requests
still reach Gemini; chat persistence and household authorization are unchanged.


Analysis attempts are persisted on each message (`pending`, `processing`,
`completed`, `skipped`, `failed`). An atomic DB claim is committed before Gemini
is called. Duplicate requests reuse the saved result/error; concurrent requests
receive `409 AI_ALREADY_ATTEMPTED`. Noise is saved as skipped before local quota
reservation. The migration marks existing chat history skipped.

Local `429 AI_RATE_LIMITED` leaves the message pending for a manual retry.
Provider quota exhaustion is `503 AI_PROVIDER_RATE_LIMITED`, with
`retryable: false`; no automatic retries occur. All provider attempts are terminal,
including failures. A crash after claiming may leave `processing`; it is never
reclaimed because Gemini might already have received the request. Add the chore
manually in that case. Analysis never creates a chore; confirmation and
`source_message_id` duplicate protection still apply.

See [TESTING.md](TESTING.md) for the isolated team test server with simulated AI
and the automated validation commands.
