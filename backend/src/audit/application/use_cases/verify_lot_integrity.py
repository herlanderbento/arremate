from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from auction.domain.entities.lot import LotId
from auction.domain.repositories.bid_repository import IBidRepository
from auction.domain.repositories.lot_repository import ILotRepository
from auction.domain.repositories.receipt_repository import IReceiptRepository
from audit.domain.hash_chain import HashChain
from audit.domain.integrity import ChainEntry, Issue, LotState, ReceiptState, verify
from shared.application.use_cases import UseCase
from shared.domain.exceptions import NotFoundException


@dataclass
class VerifyLotIntegrityInput:
    lot_id: LotId


@dataclass(frozen=True)
class AuditedBid:
    seq: int
    bidder_alias: str
    amount: Decimal
    created_at: datetime
    hash: str
    valid: bool


@dataclass(frozen=True)
class VerifyLotIntegrityOutput:
    lot_id: str
    title: str
    intact: bool
    chain_head: str
    issues: list[Issue]
    bids: list[AuditedBid]


class VerifyLotIntegrityUseCase(UseCase):
    def __init__(
        self,
        lot_repository: ILotRepository,
        bid_repository: IBidRepository,
        receipt_repository: IReceiptRepository,
        hash_chain: HashChain,
    ):
        self.lot_repository = lot_repository
        self.bid_repository = bid_repository
        self.receipt_repository = receipt_repository
        self.hash_chain = hash_chain

    async def execute(self, input: VerifyLotIntegrityInput) -> VerifyLotIntegrityOutput:
        lot = await self.lot_repository.find_by_id(input.lot_id)
        if lot is None:
            raise NotFoundException("Lote não encontrado.")
        bids = await self.bid_repository.list_by_lot(lot.id)
        receipt = await self.receipt_repository.find_by_lot_id(lot.id)

        seq_by_bid_id = {b.id: b.seq for b in bids}
        report = verify(
            self.hash_chain,
            LotState(
                lot_id=lot.id.value,
                chain_head=lot.chain_head,
                bid_count=lot.bid_count,
                current_bid=lot.current_bid,
                leader_id=lot.leader_id.value if lot.leader_id else None,
            ),
            [
                ChainEntry(
                    seq=b.seq,
                    bidder_id=b.bidder_id.value,
                    amount=b.amount,
                    created_at=b.created_at,
                    prev_hash=b.prev_hash,
                    hash=b.hash,
                )
                for b in bids
            ],
            ReceiptState(
                chain_head=receipt.chain_head,
                amount=receipt.amount,
                winner_id=receipt.winner_id.value,
                winning_bid_seq=seq_by_bid_id.get(receipt.winning_bid_id)
                if receipt.winning_bid_id
                else None,
            )
            if receipt
            else None,
        )

        return VerifyLotIntegrityOutput(
            lot_id=str(lot.id.value),
            title=lot.title,
            intact=report.intact,
            chain_head=lot.chain_head,
            issues=report.issues,
            bids=[
                AuditedBid(
                    seq=b.seq,
                    bidder_alias=self.hash_chain.alias(b.bidder_id.value, lot.id.value),
                    amount=b.amount,
                    created_at=b.created_at,
                    hash=b.hash,
                    valid=b.seq in report.valid_seqs,
                )
                for b in bids
            ],
        )
