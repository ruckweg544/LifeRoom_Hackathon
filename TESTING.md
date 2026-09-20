# Local test environment

This environment uses **simulated AI**, not Gemini. It runs on port 8002 with a
new temporary database each time. The existing port 8001 demo database is not changed. The frontend build output
is shared with the existing demo. Stop with Ctrl+C; the temporary database is removed.

After installing the normal backend/frontend dependencies, run from repo root:

```sh
backend/.venv/bin/python scripts/test_server.py
```

The launcher builds the frontend and serves it at http://127.0.0.1:8002.
API docs: http://127.0.0.1:8002/docs. The health endpoint identifies the test server.
Use two browser profiles (or a private window): create a room in one, then join
with its room code in the other. Tokens use localStorage, so two ordinary tabs
share a login.

| New chat message | Expected result |
| --- | --- |
| `[task] Do dishes` | Editable chore suggestion; no chore exists before confirmation |
| `[quota] test` | Provider quota error; no retry button |
| `[error] test` | Terminal AI error; chat remains saved |
| `ㅋㅋㅋ`, `ㅇㅇ`, `ok`, `👍` | Skipped before quota; no `[TEST AI]` console line |
| Any other text | Simulated “not a chore” |

Each actual fake-provider attempt prints `[TEST AI] provider attempt` without
message contents. Reloading chat and receiving realtime events must print no new
attempts. Repeating an analyze request in `/docs` returns the saved result/error.
The local 10-per-household/minute rate limit remains enabled: use distinct task
messages to test `429 AI_RATE_LIMITED`, rather than repeatedly analyzing one ID.

Confirm a suggestion, verify it appears for both users, and complete it from the
other profile. Verify bills and chat still synchronize. The existing
`source_message_id` constraint prevents duplicate chore creation.

Automated checks (no real Gemini quota required):

```sh
backend/.venv/bin/python -m pytest backend/app/tests -q
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run lint
```

The fake provider is installed only by this launcher, not by production startup.
This tests application behavior; it does not measure Gemini's language accuracy.


## Public team access

Start a separate tunnel to port 8002, then pass its exact HTTPS origin:

```sh
cloudflared tunnel --url http://127.0.0.1:8002 --no-autoupdate
TEST_PUBLIC_ORIGIN=https://YOUR-TUNNEL.trycloudflare.com backend/.venv/bin/python scripts/test_server.py
```

Share that tunnel URL and the room code with teammates. The local computer,
server, and tunnel must remain running. Restarting the test server creates a new
empty database; everyone must create/join a room again. AI remains simulated.
