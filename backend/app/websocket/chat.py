import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.core.security import hash_token
from app.database.session import SessionLocal
from app.models.member import Member
from app.websocket.connection_manager import manager

router = APIRouter()


@router.websocket("/ws/{household_id}")
async def websocket_chat(websocket: WebSocket, household_id: str):
    origin = websocket.headers.get("origin")
    if origin is not None and origin not in get_settings().cors_origin_list:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    try:
        auth = await asyncio.wait_for(websocket.receive_json(), timeout=5)
        if not isinstance(auth, dict) or not isinstance(auth.get("token"), str):
            raise ValueError("Missing token")
        with SessionLocal() as db:
            member = db.query(Member).filter(
                Member.session_token == hash_token(auth["token"]),
                Member.household_id == household_id,
            ).first()
            if member is None:
                raise ValueError("Invalid session")
            member_id = member.id
    except (ValueError, KeyError, TimeoutError):
        await websocket.close(code=1008)
        return
    except WebSocketDisconnect:
        return

    manager.connect(household_id, member_id, websocket)
    try:
        await websocket.send_json({"type": "ready"})
        await manager.broadcast(household_id, {"type": "presence"})
        while True:
            if (await websocket.receive())["type"] == "websocket.disconnect":
                break
            await websocket.send_json({"type": "error", "detail": "Send messages with POST /api/messages"})
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(household_id, websocket)
        await manager.broadcast(household_id, {"type": "presence"})
