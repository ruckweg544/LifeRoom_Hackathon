"""
VTHacks 룸메이트 앱 - 백엔드 (FastAPI, 단일 프로세스로 REST + WebSocket + 정적 프론트 서빙까지 다 처리)

실행:
    uvicorn main:app --reload --port 8000
그리고 브라우저에서 http://localhost:8000 열면 끝.

이 파일은 성진(프론트)/지호(백엔드)/원진(실시간+DB) 파트를 각자 다시 맡을 때python3 -m uvicorn main:app --reload --port 8000
그대로 기준으로 삼고 나눠 가져도 되는 '한 사람이 전부 짠 임시 버전'임.
"""

import json
import os
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

import database as db
import ai_service

load_dotenv()

app = FastAPI(title="VTHacks Roommate App")

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


@app.on_event("startup")
def on_startup():
    db.init_db()


# ---------------------------------------------------------------------------
# WebSocket 연결 관리 (방 코드별로 연결된 클라이언트 목록 유지)
# ---------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, List[WebSocket]] = {}

    async def connect(self, room_code: str, ws: WebSocket):
        await ws.accept()
        self.rooms.setdefault(room_code, []).append(ws)

    def disconnect(self, room_code: str, ws: WebSocket):
        if room_code in self.rooms and ws in self.rooms[room_code]:
            self.rooms[room_code].remove(ws)

    async def broadcast(self, room_code: str, event: dict):
        for ws in list(self.rooms.get(room_code, [])):
            try:
                await ws.send_text(json.dumps(event, ensure_ascii=False))
            except Exception:
                pass


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# 요청/응답 모델
# ---------------------------------------------------------------------------

class JoinRequest(BaseModel):
    name: str
    room_code: str = "demo"


class MessageCreate(BaseModel):
    sender: str
    content: str


def _row_to_message(row):
    return {
        "id": row["id"],
        "sender": row["sender"],
        "content": row["content"],
        "created_at": row["created_at"],
    }


def _row_to_chore(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "assignee": row["assignee"],
        "due_date": row["due_date"],
        "completed": bool(row["completed"]),
        "source": row["source"],
    }


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------

@app.post("/api/join")
def join(req: JoinRequest):
    room = db.get_or_create_room(req.room_code)
    db.get_or_create_user(room["id"], req.name)
    return {"room_code": room["code"], "name": req.name}


@app.get("/api/rooms/{room_code}/state")
def room_state(room_code: str):
    room = db.get_or_create_room(room_code)
    messages = [_row_to_message(r) for r in db.get_messages(room["id"])]
    chores = [_row_to_chore(r) for r in db.get_chores(room["id"])]
    return {
        "room_code": room["code"],
        "rent_due_date": room["rent_due_date"],
        "rent_amount": room["rent_amount"],
        "messages": messages,
        "chores": chores,
    }


@app.post("/api/rooms/{room_code}/messages")
async def post_message(room_code: str, body: MessageCreate):
    room = db.get_or_create_room(room_code)
    msg_row = db.add_message(room["id"], body.sender, body.content)
    msg = _row_to_message(msg_row)
    await manager.broadcast(room_code, {"type": "new_message", "message": msg})

    # AI: 이 메시지가 할일인지 감지해서, 맞으면 자동으로 chore 등록
    detection = ai_service.detect_task(body.content, sender_name=body.sender)
    new_chore = None
    if detection.get("is_task"):
        chore_row = db.add_chore(
            room["id"],
            title=detection.get("title") or "할일",
            assignee=detection.get("assignee"),
            due_date=detection.get("due_date"),
            source="ai",
        )
        new_chore = _row_to_chore(chore_row)
        await manager.broadcast(room_code, {"type": "new_chore", "chore": new_chore})

    return {"message": msg, "detected_chore": new_chore}


@app.patch("/api/chores/{chore_id}/complete")
async def complete_chore(chore_id: int, room_code: str):
    row = db.complete_chore(chore_id)
    if row is None:
        return {"error": "not found"}
    chore = _row_to_chore(row)
    await manager.broadcast(room_code, {"type": "chore_completed", "chore": chore})
    return {"chore": chore}


@app.get("/api/rooms/{room_code}/summary")
def get_summary(room_code: str):
    room = db.get_or_create_room(room_code)
    chores = db.get_chores(room["id"])
    pending = [f"{c['title']} - {c['assignee']}" if c["assignee"] else c["title"]
               for c in chores if not c["completed"]]
    done_today = [f"{c['title']} - {c['assignee']}" if c["assignee"] else c["title"]
                  for c in chores if c["completed"]]

    room_status = ai_service.RoomStatus(
        rent_due_date=room["rent_due_date"],
        rent_amount=room["rent_amount"],
        pending_chores=pending,
        completed_chores_today=done_today,
    )
    return {"summary": ai_service.daily_summary(room_status)}


# ---------------------------------------------------------------------------
# WebSocket (실시간 채팅/할일 업데이트 push)
# ---------------------------------------------------------------------------

@app.websocket("/ws/{room_code}")
async def ws_endpoint(websocket: WebSocket, room_code: str):
    await manager.connect(room_code, websocket)
    try:
        while True:
            await websocket.receive_text()  # 클라이언트는 보통 안 보내지만 연결 유지용
    except WebSocketDisconnect:
        manager.disconnect(room_code, websocket)


# ---------------------------------------------------------------------------
# 프론트엔드 정적 파일 서빙 (React 빌드 없이 바로 브라우저에서 열리게)
# ---------------------------------------------------------------------------

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def serve_index():
    return FileResponse(FRONTEND_DIR / "index.html")
