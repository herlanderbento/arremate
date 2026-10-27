from abc import ABC, abstractmethod
from decimal import Decimal

from account.domain.user import UserId
from auction.domain.entities.lot import LotId
from auction.domain.entities.receipt import Receipt


class IReceiptRepository(ABC):
    @abstractmethod
    async def insert(self, receipt: Receipt) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def find_by_lot_id(self, lot_id: LotId) -> Receipt | None:
        raise NotImplementedError()

    @abstractmethod
    async def find_by_lot_ids(self, lot_ids: list[LotId]) -> list[Receipt]:
        raise NotImplementedError()

    @abstractmethod
    async def find_by_public_token(self, public_token: str) -> Receipt | None:
        raise NotImplementedError()

    @abstractmethod
    async def list_by_winner(self, winner_id: UserId) -> list[Receipt]:
        raise NotImplementedError()

    @abstractmethod
    async def sum_amount_by_auctioneer(self, auctioneer_id: UserId) -> Decimal:
        raise NotImplementedError()
