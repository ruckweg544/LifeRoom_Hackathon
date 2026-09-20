# LifeRoom

A roommate management demo built for VTHacks: React + TypeScript + Vite,
FastAPI + SQLAlchemy + SQLite, WebSockets, and optional Gemini chore detection.

## Current features

- Households with invite codes, optional room passwords, and guest sessions.
- Persisted household chat, realtime updates, reconnect refresh, and member presence.
- Chores: create, assign, edit, complete/reopen, delete, and set due dates/times.
- Shared bills: split amounts between participants and track settlement status.
- Shared grocery lists and a household dashboard/activity feed.
- AI-assisted chores: analyze a newly sent message, review/edit the suggestion,
  then confirm creation. Chores are never created automatically.

Receipt upload/scanning, monthly recurring bills, and AI daily summaries are not
implemented. Guest sessions do not yet have expiration, recovery, or revocation.

## Run locally

Requires Python 3.11+ and Node 22.12+. From the repository root:

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

In another terminal, from the repository root:

```sh
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Open http://127.0.0.1:5173. Interactive API docs: http://127.0.0.1:8000/docs.
The Vite proxy forwards `/api` and `/ws` to port 8000. Leave `VITE_API_URL` and
`VITE_WS_URL` empty to use the current page origin; stale tunnel URLs break access.

Create a household and share its room code. Test two users with separate browser
profiles or a private window, since ordinary tabs share the localStorage session.
**Run one backend worker**: WebSocket connections and presence are process-local.

## Configuration and data

See [backend/.env.example](backend/.env.example) and
[frontend/.env.example](frontend/.env.example). The backend reads `.env` from its
working directory. Set values there or through process environment variables.

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Defaults to `sqlite:///./liferoom.db` in the backend working directory |
| `CORS_ORIGINS` | Comma-separated exact frontend origins, also checked for WebSocket connections |
| `GEMINI_API_KEY` | Optional server-side Gemini credential |
| `GEMINI_MODEL` | Model enabled for your Google project |
| `AI_TIMEZONE` | Relative-date and clock-time interpretation; defaults to `America/New_York` |

Frontend `VITE_*` values are public: never put secrets in them. `.env` files,
databases, virtual environments, and `node_modules` are Git-ignored;
`.env.example` templates are tracked.

Startup creates missing tables and applies the small additive migrations for
chore source-message links and persisted analysis state. Existing messages are
marked skipped when analysis-state columns are first added. Back up an existing
database before deployment. The retired root server is not the application entry
point; use `backend/app/main.py`.

## Chat, AI, and realtime flow

1. `POST /api/messages` saves a message and broadcasts `message.created`.
2. Only after a successful new send, the frontend calls
   `POST /api/messages/{message_id}/analyze`. History loading, refreshes, and
   rerenders never start analysis.
3. The backend checks household access and filters obvious noise before reserving
   AI quota. Skipped messages return `is_task: false` without contacting Gemini.
4. An atomic persisted claim limits Gemini to at most one attempt per message.
   Completed results, skipped states, and failures are reused on duplicate requests.
5. The user reviews the suggestion, then `POST /api/chores` saves it with
   `source_message_id`. Duplicate linked chores return `409`.

AI dates are returned as `due_date`; explicit times additionally return `due_at`
with a timezone offset. The form displays device-local time. If no clock time was
specified, it stays blank for the user to select. Unknown or ambiguous owners stay
unassigned. Results persist in the backend; suggestion cards are not restored
from chat history on page refresh.

| Analysis outcome | API behavior |
| --- | --- |
| Local limit | `429 AI_RATE_LIMITED`; manual retry allowed before a provider attempt |
| Gemini quota exhausted | `503 AI_PROVIDER_RATE_LIMITED`; no automatic retry or retry button |
| Provider failure | `503 AI_UNAVAILABLE`; attempted messages are not submitted again |
| Missing AI configuration | `503 AI_NOT_CONFIGURED` |
| Concurrent/interrupted claimed attempt | `409 AI_ALREADY_ATTEMPTED`; never automatically reclaimed |

The demo limits are 10 analyses per household per minute and 4 concurrent calls
per process, with a 15-second total timeout. A crash after claiming can leave an
unfinished analysis: it is not retried because Gemini may already have received
it. Users can still create chores manually.

Clients connect to `/ws/{household_id}` and send `{"token":"..."}` as the first
frame within five seconds. `ready`, `presence`, `message.created`, and
`household.changed` trigger REST refreshes. All reads/writes use household-scoped
bearer authentication; tokens are hashed in the database.

## Tests and public demos

From the repository root:

```sh
backend/.venv/bin/python -m pytest backend/app/tests -q
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run lint
```

Automated tests use isolated databases and mocked AI. They cover room isolation,
realtime delivery, chore/bill persistence, analysis deduplication and noise
filtering, provider errors, frontend rerenders, due times, and invalid sessions.

[TESTING.md](TESTING.md) describes the separate simulated-AI test server and
optional public tunnel. For a real-AI demo, run the normal backend with Gemini
configuration. Build the frontend to serve it from the backend on one origin.
Add the exact public HTTPS origin to `CORS_ORIGINS` and restart the backend when
the tunnel URL changes. Temporary tunnel links are not permanent deployment URLs.

## Repository layout

- `backend/app/`: APIs, models, schemas, AI service, WebSockets, and backend tests.
- `frontend/src/`: React UI, API clients, session state, and realtime hooks.
- `frontend/tests/`: React regression tests.
- `scripts/test_server.py`: isolated server with simulated AI.
- `docs/`: historical integration notes, not the current API specification.

Historical integration notes: [English](docs/BACKEND_INTEGRATION_ENG.md) ·
[한국어](docs/BACKEND_INTEGRATION_KR.md).
