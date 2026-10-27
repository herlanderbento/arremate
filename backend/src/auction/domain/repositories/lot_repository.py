from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime

from account.domain.user import UserId
from auction.domain.entities.lot import DisplayStatus, Lot, LotId
from shared.domain.repository_interface import ISearchableRepository
from shared.domain.search_input import SearchInput
from shared.domain.search_output import SearchOutput


@dataclass(frozen=True, slots=True)
class LotFilter:
    status: DisplayStatus | None = None
    text: str | None = None


@dataclass(slots=True, kw_only=True)
class LotSearchInput(SearchInput[LotFilter]):
    now: datetime


@dataclass(slots=True, kw_only=True)
class AuctioneerLotSearchInput(SearchInput[LotFilter]):
    now: datetime
    auctioneer_id: UserId


@dataclass(slots=True, kw_only=True)
class LotSearchOutput(SearchOutput[Lot]):
    pass


class ILotRepository(ISearchableRepository[Lot, LotId]):
    @abstractmethod
    async def search(self, props: LotSearchInput) -> LotSearchOutput:
        raise NotImplementedError()

    @abstractmethod
    async def search_by_auctioneer(self, props: AuctioneerLotSearchInput) -> LotSearchOutput:
        raise NotImplementedError()

    @abstractmethod
    async def list_due_for_settlement(self, now: datetime, limit: int) -> list[LotId]:
        raise NotImplementedError()

    @abstractmethod
    async def lock_by_id(self, lot_id: LotId) -> Lot | None:
        raise NotImplementedError()
