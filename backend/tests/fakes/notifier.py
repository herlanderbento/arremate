from typing import Any
from uuid import UUID

from auction.application.ports.lot_room_notifier import ILotRoomNotifier


class RecordingNotifier(ILotRoomNotifier):
    def __init__(self) -> None:
        self.events: list[tuple[UUID, dict[str, Any]]] = []

    async def publish(self, lot_id: UUID, event: dict[str, Any]) -> None:
        self.events.append((lot_id, event))

    def types(self) -> list[str]:
        return [event["type"] for _, event in self.events]
