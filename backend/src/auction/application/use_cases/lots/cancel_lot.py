from dataclasses import dataclass

from account.domain.user import UserId
from auction.application.ports.lot_room_notifier import ILotRoomNotifier
from auction.application.use_cases.common.lot_output import LotOutput
from auction.domain.entities.lot import LotId
from auction.domain.repositories.bid_repository import IBidRepository
from auction.domain.repositories.lot_repository import ILotRepository
from shared.application.clock import Clock, utc_now
from shared.application.unit_of_work import IUnitOfWork
from shared.application.use_cases import UseCase
from shared.domain.exceptions import ForbiddenException, NotFoundException
from wallet.domain.repositories.wallet_repository import IWalletRepository
from wallet.domain.repositories.wallet_transaction_repository import (
    IWalletTransactionRepository,
)


@dataclass
class CancelLotInput:
    lot_id: LotId
    auctioneer_id: UserId


class CancelLotUseCase(UseCase):
    def __init__(
        self,
        lot_repository: ILotRepository,
        bid_repository: IBidRepository,
        wallet_repository: IWalletRepository,
        transaction_repository: IWalletTransactionRepository,
        unit_of_work: IUnitOfWork,
        notifier: ILotRoomNotifier,
        clock: Clock = utc_now,
    ):
        self.lot_repository = lot_repository
        self.bid_repository = bid_repository
        self.wallet_repository = wallet_repository
        self.transaction_repository = transaction_repository
        self.unit_of_work = unit_of_work
        self.notifier = notifier
        self.clock = clock

    async def execute(self, input: CancelLotInput) -> LotOutput:
        lot = await self.lot_repository.lock_by_id(input.lot_id)
        if lot is None:
            raise NotFoundException("Lote não encontrado.")
        if lot.auctioneer_id != input.auctioneer_id:
            raise ForbiddenException("Só o leiloeiro dono pode cancelar este lote.", "NOT_OWNER")

        now = self.clock()
        leader, amount = lot.leader_id, lot.current_bid
        lot.cancel(now, allow_with_bids=True)

        if leader is not None and amount:
            wallet = (await self.wallet_repository.lock_by_user_ids({leader}))[leader]
            last_bid = await self.bid_repository.find_by_seq(lot.id, lot.bid_count)
            refund = wallet.release(amount, lot.id, last_bid.id if last_bid else None)
            await self.wallet_repository.update(wallet)
            await self.transaction_repository.insert(refund)

        await self.lot_repository.update(lot)
        await self.unit_of_work.commit()
        await self.notifier.publish(lot.id.value, {"type": "lot_cancelled", "lot_id": lot.id.value})
        return LotOutput.from_entity(lot, now)
