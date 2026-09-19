import asyncio
from collections import defaultdict

from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    def __init__(self):
        # ponytail: single process; shared pub/sub required before adding workers.
        self._rooms = defaultdict(dict)

    def connect(self, household_id: str, member_id: str, websocket: WebSocket):
        self._rooms[household_id][websocket] = member_id

    def disconnect(self, household_id: str, websocket: WebSocket):
        room = self._rooms.get(household_id)
        if room is not None:
            room.pop(websocket, None)
            if not room:
                self._rooms.pop(household_id, None)

    def room_member_ids(self, household_id: str) -> set[str]:
        return set(self._rooms.get(household_id, {}).values())

    async def broadcast(self, household_id: str, payload: dict):
        async def send(socket):
            try:
                await asyncio.wait_for(socket.send_json(payload), timeout=2)
            except (TimeoutError, WebSocketDisconnect, RuntimeError, OSError):
                self.disconnect(household_id, socket)
                try:
                    await asyncio.wait_for(socket.close(code=1013), timeout=1)
                except (TimeoutError, RuntimeError, OSError):
                    pass

        await asyncio.gather(*(send(ws) for ws in tuple(self._rooms.get(household_id, {}))))


manager = ConnectionManager()
