import logging
from typing import Any
from uuid import UUID

from fastapi import WebSocket

from auction.application.ports.lot_room_notifier import ILotRoomNotifier
from shared.infra.api.money import to_json

logger = logging.getLogger(__name__)


class ConnectionManager(ILotRoomNotifier):
    def __init__(self) -> None:
        self.rooms: dict[UUID, set[WebSocket]] = {}

    async def connect(self, lot_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self.rooms.setdefault(lot_id, set()).add(websocket)

    def disconnect(self, lot_id: UUID, websocket: WebSocket) -> None:
        room = self.rooms.get(lot_id)
        if room is None:
            return
        room.discard(websocket)
        if not room:
            del self.rooms[lot_id]

    async def publish(self, lot_id: UUID, event: dict[str, Any]) -> None:
        payload = to_json(event)
        for websocket in list(self.rooms.get(lot_id, ())):
            try:
                await websocket.send_json(payload)
            except Exception:
                self.disconnect(lot_id, websocket)


lot_rooms = ConnectionManager()


def get_lot_room_notifier() -> ILotRoomNotifier:
    return lot_rooms
