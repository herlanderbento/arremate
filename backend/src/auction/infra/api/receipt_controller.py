from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel

from auction.application.use_cases.receipts.get_receipt import (
    GetReceiptInput,
    GetReceiptUseCase,
    ReceiptOutput,
)
from auction.domain.repositories.lot_repository import ILotRepository
from auction.domain.repositories.receipt_repository import IReceiptRepository
from auction.infra.api.auction_dependencies import get_lot_repository, get_receipt_repository
from audit.domain.hash_chain import HashChain
from audit.infra.hash_chain_provider import get_hash_chain
from shared.infra.api.money import Money

router = APIRouter(prefix="/receipts", tags=["Receipts"])


class ReceiptPresenter(BaseModel):
    lot_id: UUID
    title: str
    image_url: str | None
    winner_alias: str
    amount: Money
    issued_at: datetime
    chain_head: str
    bid_count: int
    audit_url: str

    @classmethod
    def from_output(cls, o: ReceiptOutput) -> "ReceiptPresenter":
        return cls(**o.__dict__, audit_url=f"/audit/lots/{o.lot_id}")


def get_receipt_use_case(
    receipts: IReceiptRepository = Depends(get_receipt_repository),
    lots: ILotRepository = Depends(get_lot_repository),
    hash_chain: HashChain = Depends(get_hash_chain),
) -> GetReceiptUseCase:
    return GetReceiptUseCase(receipts, lots, hash_chain)


@router.get("/{token}", response_model=ReceiptPresenter, status_code=status.HTTP_200_OK)
async def get_receipt(
    token: str = Path(min_length=10, max_length=64),
    use_case: GetReceiptUseCase = Depends(get_receipt_use_case),
):
    return ReceiptPresenter.from_output(await use_case.execute(GetReceiptInput(public_token=token)))
