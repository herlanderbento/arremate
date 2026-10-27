from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from account.domain.user import UserId
from auction.domain.entities.bid import Bid, BidId
from auction.domain.entities.lot import LotId
from shared.domain.search_input import SearchInput
from shared.domain.search_output import SearchOutput


@dataclass(frozen=True, slots=True)
class BidderLotSummary:
    lot_id: LotId
    max_amount: Decimal
    last_bid_at: datetime


@dataclass(frozen=True, slots=True)
class MyBidFilter:
    text: str | None = None


@dataclass(slots=True, kw_only=True)
class MyBidSearchInput(SearchInput[MyBidFilter]):
    bidder_id: UserId


@dataclass(slots=True, kw_only=True)
class MyBidSearchOutput(SearchOutput[BidderLotSummary]):
    pass


class IBidRepository(ABC):
    @abstractmethod
    async def insert(self, bid: Bid) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def find_by_id(self, bid_id: BidId) -> Bid | None:
        raise NotImplementedError()

    @abstractmethod
    async def find_by_seq(self, lot_id: LotId, seq: int) -> Bid | None:
        raise NotImplementedError()

    @abstractmethod
    async def search_by_bidder(self, props: MyBidSearchInput) -> MyBidSearchOutput:
        raise NotImplementedError()

    @abstractmethod
    async def list_by_lot(self, lot_id: LotId) -> list[Bid]:
        raise NotImplementedError()
