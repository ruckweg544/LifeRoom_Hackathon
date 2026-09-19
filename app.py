import asyncio
import hashlib
import os
import secrets
import sqlite3
from collections import defaultdict
from contextlib import asynccontextmanager, contextmanager
from datetime import date
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, StringConstraints


Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
MessageText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Named(Input):
    name: Text


class Join(Input):
    invite_code: Text


class Message(Input):
    content: MessageText


class Chore(Input):
    title: Text
    assignee_id: str | None = None
    due_date: date | None = None


class ChoreUpdate(Input):
    completed: bool | None = Field(default=None, strict=True)
    assignee_id: str | None = None
    due_date: date | None = None


class Bill(Input):
    title: Text
    amount_cents: int = Field(gt=0, le=1_000_000_000, strict=True)
    payer_id: str
    participant_ids: list[str] = Field(min_length=1, max_length=100)


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def create_app(db_path=None):
    db_path = str(db_path or os.getenv("LIFEROOM_DB_PATH", "data/liferoom.sqlite3"))
    origins = [x.strip() for x in os.getenv(
        "LIFEROOM_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if x.strip()]
    # ponytail: one process, synchronous SQLite for demo traffic; use Postgres
    # and shared pub/sub when multiple workers or sustained throughput are needed.
    connections = defaultdict(set)

    @contextmanager
    def database():
        db = sqlite3.connect(db_path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    @asynccontextmanager
    async def lifespan(app):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with database() as db:
            db.execute("PRAGMA journal_mode = WAL")
            db.executescript(Path(__file__).with_name("schema.sql").read_text())
        yield
        connections.clear()

    app = FastAPI(title="LifeRoom Data + Realtime", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=origins,
                       allow_methods=["GET", "POST", "PATCH"],
                       allow_headers=["Authorization", "Content-Type"])

    def user_for_token(token):
        with database() as db:
            row = db.execute("SELECT id, name FROM users WHERE token_hash = ?", (digest(token),)).fetchone()
        if row is None:
            raise HTTPException(401, "Invalid session")
        return dict(row)

    def current_user(credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())]):
        return user_for_token(credentials.credentials)

    User = Annotated[dict, Depends(current_user)]

    def require_member(db, household_id, user_id):
        if not db.execute("SELECT 1 FROM members WHERE household_id = ? AND user_id = ?",
                          (household_id, user_id)).fetchone():
            raise HTTPException(403, "Household membership required")

    async def publish(household_id, event_type, entity_id):
        # Notifications invalidate saved state; clients fetch the authoritative snapshot.
        event = {"type": event_type, "household_id": household_id, "entity_id": entity_id}

        async def send(socket):
            try:
                await asyncio.wait_for(socket.send_json(event), timeout=2)
            except (TimeoutError, WebSocketDisconnect, RuntimeError, OSError):
                connections[household_id].discard(socket)
                try:
                    await asyncio.wait_for(socket.close(code=1013), timeout=1)
                except (TimeoutError, RuntimeError, OSError):
                    pass

        await asyncio.gather(*(send(ws) for ws in tuple(connections.get(household_id, ()))))

    @app.post("/sessions", status_code=201)
    async def session(body: Named):
        # Minimal guest identity until the backend team integrates its auth provider.
        user_id, token = str(uuid4()), secrets.token_urlsafe(32)
        with database() as db:
            db.execute("INSERT INTO users VALUES (?, ?, ?)", (user_id, body.name, digest(token)))
        return {"user": {"id": user_id, "name": body.name}, "token": token}

    @app.get("/households")
    async def households(user: User):
        with database() as db:
            return [dict(r) for r in db.execute(
                "SELECT h.id, h.name FROM households h JOIN members m ON m.household_id=h.id WHERE m.user_id=?",
                (user["id"],))]

    @app.post("/households", status_code=201)
    async def create_household(body: Named, user: User):
        household_id, invite = str(uuid4()), secrets.token_urlsafe(24)
        with database() as db:
            db.execute("INSERT INTO households VALUES (?, ?, ?)", (household_id, body.name, digest(invite)))
            db.execute("INSERT INTO members VALUES (?, ?)", (household_id, user["id"]))
        return {"id": household_id, "name": body.name, "invite_code": invite}

    @app.post("/households/join")
    async def join_household(body: Join, user: User):
        with database() as db:
            row = db.execute("SELECT id, name FROM households WHERE invite_hash=?", (digest(body.invite_code),)).fetchone()
            if row is None:
                raise HTTPException(404, "Invalid invite")
            added = db.execute("INSERT OR IGNORE INTO members VALUES (?, ?)", (row["id"], user["id"])).rowcount
        if added:
            await publish(row["id"], "member.joined", user["id"])
        return dict(row)

    @app.get("/households/{household_id}/state")
    async def state(household_id: str, user: User):
        with database() as db:
            db.execute("BEGIN")
            require_member(db, household_id, user["id"])
            members = [dict(r) for r in db.execute(
                "SELECT u.id, u.name FROM users u JOIN members m ON m.user_id=u.id WHERE m.household_id=? ORDER BY u.id",
                (household_id,))]
            messages = [dict(r) for r in db.execute(
                "SELECT * FROM messages WHERE household_id=? ORDER BY rowid", (household_id,))]
            chores = [dict(r) for r in db.execute(
                "SELECT * FROM chores WHERE household_id=? ORDER BY rowid", (household_id,))]
            for chore in chores:
                chore["completed"] = bool(chore["completed"])
            bills = [dict(r) for r in db.execute(
                "SELECT * FROM bills WHERE household_id=? ORDER BY rowid", (household_id,))]
            shares_by_bill = defaultdict(list)
            for row in db.execute(
                "SELECT s.bill_id, s.user_id, s.amount_cents FROM bill_shares s "
                "JOIN bills b ON b.id=s.bill_id WHERE b.household_id=? ORDER BY s.user_id",
                (household_id,),
            ):
                shares_by_bill[row["bill_id"]].append(
                    {"user_id": row["user_id"], "amount_cents": row["amount_cents"]})
            balances = {m["id"]: 0 for m in members}
            for bill in bills:
                bill["shares"] = shares_by_bill[bill["id"]]
                balances[bill["payer_id"]] += bill["amount_cents"]
                for share in bill["shares"]:
                    balances[share["user_id"]] -= share["amount_cents"]
        return {"household_id": household_id, "members": members, "messages": messages,
                "chores": chores, "bills": bills, "balances_cents": balances}

    @app.post("/households/{household_id}/messages", status_code=201)
    async def message(household_id: str, body: Message, user: User):
        message_id = str(uuid4())
        with database() as db:
            require_member(db, household_id, user["id"])
            db.execute("INSERT INTO messages (id, household_id, sender_id, content) VALUES (?, ?, ?, ?)",
                       (message_id, household_id, user["id"], body.content))
            saved = dict(db.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone())
        await publish(household_id, "message.created", message_id)
        return saved

    @app.post("/households/{household_id}/chores", status_code=201)
    async def chore(household_id: str, body: Chore, user: User):
        chore_id = str(uuid4())
        with database() as db:
            require_member(db, household_id, user["id"])
            if body.assignee_id is not None:
                require_member(db, household_id, body.assignee_id)
            db.execute("INSERT INTO chores (id, household_id, created_by, title, assignee_id, due_date) VALUES (?, ?, ?, ?, ?, ?)",
                       (chore_id, household_id, user["id"], body.title, body.assignee_id,
                        body.due_date.isoformat() if body.due_date else None))
        await publish(household_id, "chore.created", chore_id)
        return {"id": chore_id, "household_id": household_id, "created_by": user["id"],
                **body.model_dump(mode="json"), "completed": False}

    @app.patch("/households/{household_id}/chores/{chore_id}")
    async def update_chore(household_id: str, chore_id: str, body: ChoreUpdate, user: User):
        updates = body.model_dump(mode="json", exclude_unset=True)
        if not updates or ("completed" in updates and updates["completed"] is None):
            raise HTTPException(422, "Provide an update; completed must be a boolean")
        with database() as db:
            require_member(db, household_id, user["id"])
            if updates.get("assignee_id") is not None:
                require_member(db, household_id, updates["assignee_id"])
            # Keys come exclusively from the validated model, never raw input.
            columns = ", ".join(f"{key}=?" for key in updates)
            changed = db.execute(f"UPDATE chores SET {columns} WHERE id=? AND household_id=?",
                                 (*updates.values(), chore_id, household_id)).rowcount
            if not changed:
                raise HTTPException(404, "Chore not found")
            saved = dict(db.execute("SELECT * FROM chores WHERE id=?", (chore_id,)).fetchone())
        saved["completed"] = bool(saved["completed"])
        await publish(household_id, "chore.updated", chore_id)
        return saved

    @app.post("/households/{household_id}/bills", status_code=201)
    async def bill(household_id: str, body: Bill, user: User):
        participants = sorted(set(body.participant_ids))
        if len(participants) != len(body.participant_ids):
            raise HTTPException(422, "Duplicate participants")
        bill_id = str(uuid4())
        quotient, remainder = divmod(body.amount_cents, len(participants))
        shares = [{"user_id": uid, "amount_cents": quotient + (i < remainder)} for i, uid in enumerate(participants)]
        with database() as db:
            for uid in {user["id"], body.payer_id, *participants}:
                require_member(db, household_id, uid)
            db.execute("INSERT INTO bills VALUES (?, ?, ?, ?, ?, ?)",
                       (bill_id, household_id, user["id"], body.payer_id, body.title, body.amount_cents))
            db.executemany("INSERT INTO bill_shares VALUES (?, ?, ?, ?)",
                           [(bill_id, household_id, s["user_id"], s["amount_cents"]) for s in shares])
        await publish(household_id, "bill.created", bill_id)
        return {"id": bill_id, "household_id": household_id, "created_by": user["id"],
                "title": body.title, "payer_id": body.payer_id, "amount_cents": body.amount_cents, "shares": shares}

    @app.websocket("/households/{household_id}/events")
    async def events(socket: WebSocket, household_id: str):
        origin = socket.headers.get("origin")
        if origin is not None and origin not in origins:
            await socket.close(code=1008)
            return
        await socket.accept()
        try:
            # First frame avoids exposing bearer credentials in URLs/access logs.
            auth = await asyncio.wait_for(socket.receive_json(), timeout=5)
            if not isinstance(auth, dict) or not isinstance(auth.get("token"), str):
                raise ValueError("Missing token")
            user = user_for_token(auth["token"])
            with database() as db:
                require_member(db, household_id, user["id"])
        except (HTTPException, ValueError, KeyError, TimeoutError):
            await socket.close(code=1008)
            return
        except WebSocketDisconnect:
            return
        connections[household_id].add(socket)
        try:
            await socket.send_json({"type": "ready", "household_id": household_id})
            while True:
                if (await socket.receive())["type"] == "websocket.disconnect":
                    break
        except WebSocketDisconnect:
            pass
        finally:
            connections[household_id].discard(socket)
            if not connections[household_id]:
                del connections[household_id]

    return app


app = create_app()
