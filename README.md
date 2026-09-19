# LifeRoom

Roommate household demo: React + TypeScript + Vite frontend, FastAPI + SQLAlchemy
+ SQLite backend. Built on `feature/data-realtime`, incorporating the supplied
integration ZIP and the existing room isolation, commit-before-notify, reconnect,
and integer-money approach.

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

The original standalone implementation is preserved at root (`app.py`,
`schema.sql`, `test_app.py`); its tests run with `.venv/bin/python -m unittest -v test_app`
from the root. See [its original contract](DATA_REALTIME_REFERENCE.md). It is a
reference/regression baseline, **not** the server used by this React frontend.
Do not point both implementations at the same database: schemas are different.
No existing databases, sessions, or ZIP seed databases were migrated or overwritten.

## ZIP corrections and scope

The supplied archive had empty `src/components` folders, so the missing UI was
restored to match its existing pages. Chore/bill updates had no room notifications;
those and reconnect refreshes now use the Data + Realtime approach. Cross-household
chore reassignment, null patch failures, fractional-cent bills, raw stored session
tokens, multi-tab presence, and repeated bill queries were corrected. The seed
script now leaves an existing demo household untouched. The frontend development
server/router dependencies were updated after the imported lockfile reported
known vulnerabilities.

AI code was absent from the ZIP (confirmed by the user). AI, receipt scanning and
monthly recurring expenses are not implemented here. The ZIP's existing grocery
pages remain; no new grocery feature scope was added. Browser interaction testing
was unavailable in the connected environment; use the two-profile flow above for
visual acceptance.
