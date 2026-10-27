from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from account.domain.user import UserId
from auction.application.use_cases.common.lot_output import LotOutput
from auction.domain.entities.lot import Lot, LotStatus
from auction.domain.entities.receipt import Receipt
from auction.domain.repositories.bid_repository import (
    IBidRepository,
    MyBidFilter,
    MyBidSearchInput,
)
from auction.domain.repositories.lot_repository import ILotRepository
from auction.domain.repositories.receipt_repository import IReceiptRepository
from audit.domain.hash_chain import HashChain
from shared.application.clock import Clock, utc_now
from shared.application.paginated_list_input import PaginatedListInput
from shared.application.paginated_list_output import PaginatedListOutput
from shared.application.use_cases import UseCase


class BidSituation(str, Enum):
    WINNING = "winning"
    OUTBID = "outbid"
    WON = "won"
    LOST = "lost"
    CANCELLED = "cancelled"


@dataclass(slots=True, kw_only=True)
class ListMyBidsInput(PaginatedListInput[MyBidFilter]):
    bidder_id: UserId


@dataclass(frozen=True)
class MyBidOutput:
    lot: LotOutput
    my_max_bid: Decimal
    my_alias: str
    situation: BidSituation
    receipt_token: str | None


@dataclass(slots=True)
class ListMyBidsOutput(PaginatedListOutput[MyBidOutput]):
    pass


class ListMyBidsUseCase(UseCase):
    def __init__(
        self,
        bid_repository: IBidRepository,
        lot_repository: ILotRepository,
        receipt_repository: IReceiptRepository,
        hash_chain: HashChain,
        clock: Clock = utc_now,
    ):
        self.bid_repository = bid_repository
        self.lot_repository = lot_repository
        self.receipt_repository = receipt_repository
        self.hash_chain = hash_chain
        self.clock = clock

    async def execute(self, input: ListMyBidsInput) -> ListMyBidsOutput:
        search_output = await self.bid_repository.search_by_bidder(
            MyBidSearchInput(bidder_id=input.bidder_id, **input.to_search_input())
        )
        lot_ids = [s.lot_id for s in search_output.items]
        if lot_ids:
            lots = {lot.id: lot for lot in await self.lot_repository.find_by_ids(set(lot_ids))}
            receipts = {r.lot_id: r for r in await self.receipt_repository.find_by_lot_ids(lot_ids)}
        else:
            lots, receipts = {}, {}

        now = self.clock()
        items = []
        for summary in search_output.items:
            lot = lots.get(summary.lot_id)
            if lot is None:
                continue
            receipt = receipts.get(lot.id)
            situation = self._situation(lot, receipt, input.bidder_id)
            items.append(
                MyBidOutput(
                    lot=LotOutput.from_entity(lot, now),
                    my_max_bid=summary.max_amount,
                    my_alias=self.hash_chain.alias(input.bidder_id.value, lot.id.value),
                    situation=situation,
                    receipt_token=receipt.public_token if situation == BidSituation.WON else None,
                )
            )
        return ListMyBidsOutput(
            items=items,
            total=search_output.total,
            current_page=search_output.current_page,
            per_page=search_output.per_page,
            last_page=search_output.last_page,
        )

    @staticmethod
    def _situation(lot: Lot, receipt: Receipt | None, bidder_id: UserId) -> BidSituation:
        if lot.status == LotStatus.CANCELLED:
            return BidSituation.CANCELLED
        if lot.status == LotStatus.SETTLED:
            won = receipt is not None and receipt.winner_id == bidder_id
            return BidSituation.WON if won else BidSituation.LOST
        return BidSituation.WINNING if lot.leader_id == bidder_id else BidSituation.OUTBID
