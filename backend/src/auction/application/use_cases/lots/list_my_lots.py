from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from account.domain.user import UserId
from auction.application.use_cases.common.lot_output import LotOutput
from auction.domain.entities.lot import LotId
from auction.domain.entities.receipt import Receipt
from auction.domain.repositories.lot_repository import (
    AuctioneerLotSearchInput,
    ILotRepository,
    LotFilter,
    LotSearchOutput,
)
from auction.domain.repositories.receipt_repository import IReceiptRepository
from audit.domain.hash_chain import HashChain
from shared.application.clock import Clock, utc_now
from shared.application.paginated_list_input import PaginatedListInput
from shared.application.paginated_list_output import PaginatedListOutput
from shared.application.use_cases import UseCase


@dataclass(slots=True, kw_only=True)
class ListMyLotsInput(PaginatedListInput[LotFilter]):
    auctioneer_id: UserId


@dataclass(frozen=True)
class MyLotOutput:
    lot: LotOutput
    sold: bool
    final_amount: Decimal | None
    winner_alias: str | None


@dataclass(slots=True)
class ListMyLotsOutput(PaginatedListOutput[MyLotOutput]):
    total_received: Decimal


class ListMyLotsUseCase(UseCase):
    def __init__(
        self,
        lot_repository: ILotRepository,
        receipt_repository: IReceiptRepository,
        hash_chain: HashChain,
        clock: Clock = utc_now,
    ):
        self.lot_repository = lot_repository
        self.receipt_repository = receipt_repository
        self.hash_chain = hash_chain
        self.clock = clock

    async def execute(self, input: ListMyLotsInput) -> ListMyLotsOutput:
        now = self.clock()
        search_output = await self.lot_repository.search_by_auctioneer(
            AuctioneerLotSearchInput(
                now=now, auctioneer_id=input.auctioneer_id, **input.to_search_input()
            )
        )
        found = await self.receipt_repository.find_by_lot_ids([lot.id for lot in search_output.items])
        total_received = await self.receipt_repository.sum_amount_by_auctioneer(input.auctioneer_id)
        return self.__to_output(search_output, {r.lot_id: r for r in found}, total_received, now)

    def __to_output(
        self,
        search_output: LotSearchOutput,
        receipts: dict[LotId, Receipt],
        total_received: Decimal,
        now: datetime,
    ) -> ListMyLotsOutput:
        items = []
        for lot in search_output.items:
            receipt = receipts.get(lot.id)
            items.append(
                MyLotOutput(
                    lot=LotOutput.from_entity(lot, now),
                    sold=receipt is not None,
                    final_amount=receipt.amount if receipt else None,
                    winner_alias=(
                        self.hash_chain.alias(receipt.winner_id.value, lot.id.value)
                        if receipt
                        else None
                    ),
                )
            )
        return ListMyLotsOutput(
            items=items,
            total=search_output.total,
            current_page=search_output.current_page,
            per_page=search_output.per_page,
            last_page=search_output.last_page,
            total_received=total_received,
        )
