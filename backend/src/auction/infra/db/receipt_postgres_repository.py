from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from account.domain.user import UserId
from auction.domain.entities.bid import BidId
from auction.domain.entities.lot import LotId
from auction.domain.entities.receipt import Receipt, ReceiptId
from auction.domain.repositories.receipt_repository import IReceiptRepository
from auction.infra.db.sql_models import LotModel, ReceiptModel
from shared.domain.money import money
from shared.utils.datetime_utils import to_aware_utc


def _to_model(entity: Receipt) -> ReceiptModel:
    return ReceiptModel(
        id=entity.id.value,
        lot_id=entity.lot_id.value,
        winner_id=entity.winner_id.value,
        winning_bid_id=entity.winning_bid_id.value if entity.winning_bid_id else None,
        amount=entity.amount,
        chain_head=entity.chain_head,
        public_token=entity.public_token,
        issued_at=entity.issued_at,
    )


def _to_entity(model: ReceiptModel) -> Receipt:
    return Receipt(
        id=ReceiptId(value=model.id),
        lot_id=LotId(value=model.lot_id),
        winner_id=UserId(value=model.winner_id),
        winning_bid_id=BidId(value=model.winning_bid_id) if model.winning_bid_id else None,
        amount=money(model.amount),
        chain_head=str(model.chain_head).strip(),
        public_token=model.public_token,
        issued_at=to_aware_utc(model.issued_at),
    )


class ReceiptPostgresRepository(IReceiptRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert(self, receipt: Receipt) -> None:
        self.session.add(_to_model(receipt))
        await self.session.flush()

    async def find_by_lot_id(self, lot_id: LotId) -> Receipt | None:
        result = await self.session.execute(
            select(ReceiptModel).where(ReceiptModel.lot_id == lot_id.value)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def find_by_lot_ids(self, lot_ids: list[LotId]) -> list[Receipt]:
        if not lot_ids:
            return []
        result = await self.session.execute(
            select(ReceiptModel).where(ReceiptModel.lot_id.in_([i.value for i in lot_ids]))
        )
        return [_to_entity(model) for model in result.scalars().all()]

    async def find_by_public_token(self, public_token: str) -> Receipt | None:
        result = await self.session.execute(
            select(ReceiptModel).where(ReceiptModel.public_token == public_token)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_by_winner(self, winner_id: UserId) -> list[Receipt]:
        result = await self.session.execute(
            select(ReceiptModel).where(ReceiptModel.winner_id == winner_id.value)
        )
        return [_to_entity(model) for model in result.scalars().all()]

    async def sum_amount_by_auctioneer(self, auctioneer_id: UserId) -> Decimal:
        result = await self.session.execute(
            select(func.coalesce(func.sum(ReceiptModel.amount), 0))
            .join(LotModel, LotModel.id == ReceiptModel.lot_id)
            .where(LotModel.auctioneer_id == auctioneer_id.value)
        )
        return money(result.scalar_one())
