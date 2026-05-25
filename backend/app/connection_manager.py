import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # room_code -> {player_id -> WebSocket}
        self._connections: dict[str, dict[int, WebSocket]] = {}

    def _room(self, room_code: str) -> dict[int, WebSocket]:
        return self._connections.setdefault(room_code, {})

    async def connect(self, websocket: WebSocket, room_code: str, player_id: int) -> None:
        await websocket.accept()
        self._room(room_code)[player_id] = websocket

    def disconnect(self, room_code: str, player_id: int) -> None:
        room = self._connections.get(room_code, {})
        room.pop(player_id, None)
        if not room:
            self._connections.pop(room_code, None)

    async def send_personal(self, player_id: int, room_code: str, message: dict) -> None:
        ws = self._room(room_code).get(player_id)
        if ws:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                pass

    async def broadcast(self, room_code: str, message: dict, exclude: int | None = None) -> None:
        payload = json.dumps(message)
        dead: list[int] = []
        for pid, ws in list(self._room(room_code).items()):
            if pid == exclude:
                continue
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(pid)
        for pid in dead:
            self._room(room_code).pop(pid, None)

    def player_ids(self, room_code: str) -> list[int]:
        return list(self._room(room_code).keys())

    def is_connected(self, room_code: str, player_id: int) -> bool:
        return player_id in self._room(room_code)


manager = ConnectionManager()
