from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from auction.domain.repositories.lot_repository import ILotRepository
from auction.domain.repositories.receipt_repository import IReceiptRepository
from audit.domain.hash_chain import HashChain
from shared.application.use_cases import UseCase
from shared.domain.exceptions import NotFoundException


@dataclass
class GetReceiptInput:
    public_token: str


@dataclass(frozen=True)
class ReceiptOutput:
    lot_id: UUID
    title: str
    image_url: str | None
    winner_alias: str
    amount: Decimal
    issued_at: datetime
    chain_head: str
    bid_count: int


class GetReceiptUseCase(UseCase):
    def __init__(
        self,
        receipt_repository: IReceiptRepository,
        lot_repository: ILotRepository,
        hash_chain: HashChain,
    ):
        self.receipt_repository = receipt_repository
        self.lot_repository = lot_repository
        self.hash_chain = hash_chain

    async def execute(self, input: GetReceiptInput) -> ReceiptOutput:
        receipt = await self.receipt_repository.find_by_public_token(input.public_token)

        lot = await self.lot_repository.find_by_id(receipt.lot_id) if receipt else None

        if receipt is None or lot is None:
            raise NotFoundException("Comprovante não encontrado.")

        return ReceiptOutput(
            lot_id=lot.id.value,
            title=lot.title,
            image_url=lot.image_url,
            winner_alias=self.hash_chain.alias(receipt.winner_id.value, lot.id.value),
            amount=receipt.amount,
            issued_at=receipt.issued_at,
            chain_head=receipt.chain_head,
            bid_count=lot.bid_count,
        )
