from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from account.domain.user import UserId, UserRole
from auction.application.ports.lot_room_notifier import ILotRoomNotifier
from auction.domain.entities.bid import Bid, BidId
from auction.domain.entities.lot import LotId
from auction.domain.repositories.bid_repository import IBidRepository
from auction.domain.repositories.lot_repository import ILotRepository
from audit.domain.hash_chain import HashChain
from shared.application.clock import Clock, utc_now
from shared.application.unit_of_work import IUnitOfWork
from shared.application.use_cases import UseCase
from shared.domain.exceptions import ConflictException, ForbiddenException, NotFoundException
from wallet.domain.repositories.wallet_repository import IWalletRepository
from wallet.domain.repositories.wallet_transaction_repository import (
    IWalletTransactionRepository,
)


@dataclass
class PlaceBidInput:
    lot_id: LotId
    bidder_id: UserId
    bidder_role: UserRole
    amount: Decimal


@dataclass(frozen=True)
class PlaceBidOutput:
    seq: int
    amount: Decimal
    bidder_alias: str
    created_at: datetime
    ends_at: datetime
    extended: bool
    min_next_bid: Decimal
    bid_count: int
    available: Decimal


class PlaceBidUseCase(UseCase):
    def __init__(
        self,
        lot_repository: ILotRepository,
        bid_repository: IBidRepository,
        wallet_repository: IWalletRepository,
        transaction_repository: IWalletTransactionRepository,
        hash_chain: HashChain,
        unit_of_work: IUnitOfWork,
        notifier: ILotRoomNotifier,
        clock: Clock = utc_now,
    ):
        self.lot_repository = lot_repository
        self.bid_repository = bid_repository
        self.wallet_repository = wallet_repository
        self.transaction_repository = transaction_repository
        self.hash_chain = hash_chain
        self.unit_of_work = unit_of_work
        self.notifier = notifier
        self.clock = clock

    async def execute(self, input: PlaceBidInput) -> PlaceBidOutput:
        if input.bidder_role != UserRole.BIDDER:
            raise ForbiddenException(
                "Leiloeiros não podem dar lances.", code="AUCTIONEER_CANNOT_BID"
            )

        lot = await self.lot_repository.lock_by_id(input.lot_id)
        if lot is None:
            raise NotFoundException("Lote não encontrado.")

        now = self.clock()
        lot.check_bid(input.bidder_id, input.amount, now)

        previous_leader = lot.leader_id
        wallets = await self.wallet_repository.lock_by_user_ids(
            {input.bidder_id} | ({previous_leader} if previous_leader else set())
        )
        bidder_wallet = wallets.get(input.bidder_id)
        if bidder_wallet is None:
            raise NotFoundException("Carteira não encontrada.")

        bid = await self._chain_bid(lot.id, lot.bid_count + 1, input, now)
        hold = bidder_wallet.hold(input.amount, lot.id, bid.id)
        outcome = lot.apply_bid(
            input.bidder_id,
            input.amount,
            now,
            self.hash_chain.chain_head(lot.id.value, bid.seq, bid.hash),
        )

        await self.bid_repository.insert(bid)
        await self.lot_repository.update(lot)
        await self.wallet_repository.update(bidder_wallet)
        await self.transaction_repository.insert(hold)
        if outcome.previous_leader_id is not None and outcome.previous_amount:
            previous_wallet = wallets[outcome.previous_leader_id]
            release = previous_wallet.release(outcome.previous_amount, lot.id, bid.id)
            await self.wallet_repository.update(previous_wallet)
            await self.transaction_repository.insert(release)

        await self.unit_of_work.commit()

        alias = self.hash_chain.alias(input.bidder_id.value, lot.id.value)
        await self.notifier.publish(
            lot.id.value,
            {
                "type": "bid_placed",
                "lot_id": lot.id.value,
                "seq": bid.seq,
                "amount": bid.amount,
                "bidder_alias": alias,
                "created_at": bid.created_at,
                "ends_at": lot.ends_at,
                "min_next_bid": lot.min_next_bid(),
                "bid_count": lot.bid_count,
            },
        )
        if outcome.extended:
            await self.notifier.publish(
                lot.id.value,
                {"type": "lot_extended", "lot_id": lot.id.value, "ends_at": lot.ends_at},
            )

        return PlaceBidOutput(
            seq=bid.seq,
            amount=bid.amount,
            bidder_alias=alias,
            created_at=bid.created_at,
            ends_at=lot.ends_at,
            extended=outcome.extended,
            min_next_bid=lot.min_next_bid(),
            bid_count=lot.bid_count,
            available=bidder_wallet.available,
        )

    async def _chain_bid(self, lot_id: LotId, seq: int, input: PlaceBidInput, now: datetime) -> Bid:
        if seq == 1:
            prev_hash = self.hash_chain.genesis(lot_id.value)
        else:
            previous = await self.bid_repository.find_by_seq(lot_id, seq - 1)
            if previous is None:
                raise ConflictException(
                    "O histórico deste lote está inconsistente.", "LOT_INTEGRITY_ERROR"
                )
            prev_hash = previous.hash

        bid_id = BidId()
        return Bid(
            id=bid_id,
            lot_id=lot_id,
            seq=seq,
            bidder_id=input.bidder_id,
            amount=input.amount,
            created_at=now,
            prev_hash=prev_hash,
            hash=self.hash_chain.bid_hash(
                prev_hash, lot_id.value, seq, input.bidder_id.value, input.amount, now
            ),
        )
