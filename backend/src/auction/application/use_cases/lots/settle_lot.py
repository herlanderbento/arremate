import secrets
from dataclasses import dataclass

from auction.application.ports.lot_room_notifier import ILotRoomNotifier
from auction.domain.entities.lot import LotId
from auction.domain.entities.receipt import Receipt
from auction.domain.repositories.bid_repository import IBidRepository
from auction.domain.repositories.lot_repository import ILotRepository
from auction.domain.repositories.receipt_repository import IReceiptRepository
from audit.domain.hash_chain import HashChain
from shared.application.clock import Clock, utc_now
from shared.application.unit_of_work import IUnitOfWork
from shared.application.use_cases import UseCase
from shared.domain.exceptions import ConflictException
from wallet.domain.repositories.wallet_repository import IWalletRepository
from wallet.domain.repositories.wallet_transaction_repository import (
    IWalletTransactionRepository,
)


@dataclass
class SettleLotInput:
    lot_id: LotId


class SettleLotUseCase(UseCase):
    def __init__(
        self,
        lot_repository: ILotRepository,
        bid_repository: IBidRepository,
        wallet_repository: IWalletRepository,
        transaction_repository: IWalletTransactionRepository,
        receipt_repository: IReceiptRepository,
        hash_chain: HashChain,
        unit_of_work: IUnitOfWork,
        notifier: ILotRoomNotifier,
        clock: Clock = utc_now,
    ):
        self.lot_repository = lot_repository
        self.bid_repository = bid_repository
        self.wallet_repository = wallet_repository
        self.transaction_repository = transaction_repository
        self.receipt_repository = receipt_repository
        self.hash_chain = hash_chain
        self.unit_of_work = unit_of_work
        self.notifier = notifier
        self.clock = clock

    async def execute(self, input: SettleLotInput) -> bool:
        lot = await self.lot_repository.lock_by_id(input.lot_id)
        now = self.clock()
        if lot is None or not lot.is_due_for_settlement(now):
            return False

        winner_alias = None
        amount = lot.current_bid
        if lot.leader_id is not None and amount:
            winning_bid = await self.bid_repository.find_by_seq(lot.id, lot.bid_count)
            if winning_bid is None or winning_bid.bidder_id != lot.leader_id:
                raise ConflictException(
                    "O histórico deste lote está inconsistente.", "LOT_INTEGRITY_ERROR"
                )

            wallets = await self.wallet_repository.lock_by_user_ids(
                {lot.leader_id, lot.auctioneer_id}
            )
            winner, auctioneer = wallets[lot.leader_id], wallets[lot.auctioneer_id]
            debit = winner.debit(amount, lot.id)
            credit = auctioneer.credit(amount, lot.id)

            await self.receipt_repository.insert(
                Receipt(
                    lot_id=lot.id,
                    winner_id=lot.leader_id,
                    winning_bid_id=winning_bid.id,
                    amount=amount,
                    chain_head=lot.chain_head,
                    public_token=secrets.token_urlsafe(32),
                    issued_at=now,
                )
            )
            for wallet, entry in ((winner, debit), (auctioneer, credit)):
                await self.wallet_repository.update(wallet)
                await self.transaction_repository.insert(entry)
            winner_alias = self.hash_chain.alias(lot.leader_id.value, lot.id.value)

        lot.mark_settled(now)

        await self.lot_repository.update(lot)
        await self.unit_of_work.commit()

        await self.notifier.publish(
            lot.id.value,
            {
                "type": "lot_closed",
                "lot_id": lot.id.value,
                "winner_alias": winner_alias,
                "final_amount": amount if winner_alias else None,
            },
        )
        return True
