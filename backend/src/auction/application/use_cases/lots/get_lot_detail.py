from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from account.domain.user import UserId
from auction.application.use_cases.common.lot_output import LotOutput
from auction.domain.entities.lot import LotId, LotStatus
from auction.domain.repositories.bid_repository import IBidRepository
from auction.domain.repositories.lot_repository import ILotRepository
from audit.domain.hash_chain import HashChain
from shared.application.clock import Clock, utc_now
from shared.application.use_cases import UseCase
from shared.domain.exceptions import NotFoundException


@dataclass
class GetLotDetailInput:
    lot_id: LotId
    bidder_id: UserId | None = None


@dataclass(frozen=True)
class BidHistoryItem:
    seq: int
    bidder_alias: str
    amount: Decimal
    created_at: datetime


@dataclass(frozen=True)
class LotDetailOutput:
    lot: LotOutput
    server_time: datetime
    bids: list[BidHistoryItem]
    leader_alias: str | None
    my_alias: str | None


class GetLotDetailUseCase(UseCase):
    def __init__(
        self,
        lot_repository: ILotRepository,
        bid_repository: IBidRepository,
        hash_chain: HashChain,
        settle_lot: Callable[[LotId], Awaitable[None]] | None = None,
        clock: Clock = utc_now,
    ):
        self.lot_repository = lot_repository
        self.bid_repository = bid_repository
        self.hash_chain = hash_chain
        self.settle_lot = settle_lot
        self.clock = clock

    async def execute(self, input: GetLotDetailInput) -> LotDetailOutput:
        lot = await self.lot_repository.find_by_id(input.lot_id)
        if lot is None or lot.status == LotStatus.CANCELLED:
            raise NotFoundException("Lote não encontrado.")

        if self.settle_lot is not None and lot.is_due_for_settlement(self.clock()):
            await self.settle_lot(lot.id)
            lot = await self.lot_repository.find_by_id(input.lot_id)
            assert lot is not None

        now = self.clock()
        alias = self.hash_chain.alias
        bids = await self.bid_repository.list_by_lot(lot.id)
        return LotDetailOutput(
            lot=LotOutput.from_entity(lot, now),
            server_time=now,
            bids=[
                BidHistoryItem(
                    seq=b.seq,
                    bidder_alias=alias(b.bidder_id.value, lot.id.value),
                    amount=b.amount,
                    created_at=b.created_at,
                )
                for b in reversed(bids)
            ],
            leader_alias=alias(lot.leader_id.value, lot.id.value) if lot.leader_id else None,
            my_alias=alias(input.bidder_id.value, lot.id.value) if input.bidder_id else None,
        )
