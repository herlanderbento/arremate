from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class ILotRoomNotifier(ABC):
    @abstractmethod
    async def publish(self, lot_id: UUID, event: dict[str, Any]) -> None:
        raise NotImplementedError()
