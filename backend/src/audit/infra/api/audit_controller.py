from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from auction.domain.entities.lot import LotId
from auction.domain.repositories.bid_repository import IBidRepository
from auction.domain.repositories.lot_repository import ILotRepository
from auction.domain.repositories.receipt_repository import IReceiptRepository
from auction.infra.api.auction_dependencies import (
    get_bid_repository,
    get_lot_repository,
    get_receipt_repository,
)
from audit.application.use_cases.verify_lot_integrity import (
    VerifyLotIntegrityInput,
    VerifyLotIntegrityOutput,
    VerifyLotIntegrityUseCase,
)
from audit.domain.hash_chain import HashChain
from audit.infra.hash_chain_provider import get_hash_chain
from shared.infra.api.money import Money

router = APIRouter(prefix="/audit", tags=["Audit"])


class IssuePresenter(BaseModel):
    seq: int | None
    reason: str


class AuditedBidPresenter(BaseModel):
    seq: int
    bidder_alias: str
    amount: Money
    created_at: datetime
    hash: str
    valid: bool


class AuditPresenter(BaseModel):
    lot_id: str
    title: str
    status: str
    chain_head: str
    issues: list[IssuePresenter]
    bids: list[AuditedBidPresenter]

    @classmethod
    def from_output(cls, o: VerifyLotIntegrityOutput) -> "AuditPresenter":
        return cls(
            lot_id=o.lot_id,
            title=o.title,
            status="INTACT" if o.intact else "TAMPERED",
            chain_head=o.chain_head,
            issues=[IssuePresenter(seq=i.seq, reason=i.reason.value) for i in o.issues],
            bids=[AuditedBidPresenter(**b.__dict__) for b in o.bids],
        )


def get_verify_lot_integrity_use_case(
    lots: ILotRepository = Depends(get_lot_repository),
    bids: IBidRepository = Depends(get_bid_repository),
    receipts: IReceiptRepository = Depends(get_receipt_repository),
    hash_chain: HashChain = Depends(get_hash_chain),
) -> VerifyLotIntegrityUseCase:
    return VerifyLotIntegrityUseCase(lots, bids, receipts, hash_chain)


@router.get("/lots/{lot_id}", response_model=AuditPresenter, status_code=status.HTTP_200_OK)
async def audit_lot(
    lot_id: UUID,
    use_case: VerifyLotIntegrityUseCase = Depends(get_verify_lot_integrity_use_case),
):
    output = await use_case.execute(VerifyLotIntegrityInput(lot_id=LotId(value=lot_id)))
    return AuditPresenter.from_output(output)
