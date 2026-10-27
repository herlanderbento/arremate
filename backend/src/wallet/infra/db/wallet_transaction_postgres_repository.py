from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auction.domain.entities.bid import BidId
from auction.domain.entities.lot import LotId
from shared.domain.money import money
from shared.utils.datetime_utils import to_aware_utc
from wallet.domain.entities.wallet import WalletId
from wallet.domain.entities.wallet_transaction import (
    WalletTransaction,
    WalletTransactionId,
    WalletTransactionType,
)
from wallet.domain.repositories.wallet_transaction_repository import (
    IWalletTransactionRepository,
)
from wallet.infra.db.sql_models import WalletTransactionModel


def _to_model(entity: WalletTransaction) -> WalletTransactionModel:
    return WalletTransactionModel(
        id=entity.id.value,
        wallet_id=entity.wallet_id.value,
        type=entity.type.value,
        amount=entity.amount,
        lot_id=entity.lot_id.value if entity.lot_id else None,
        bid_id=entity.bid_id.value if entity.bid_id else None,
        created_at=entity.created_at,
    )


def _to_entity(model: WalletTransactionModel) -> WalletTransaction:
    return WalletTransaction(
        id=WalletTransactionId(value=model.id),
        wallet_id=WalletId(value=model.wallet_id),
        type=WalletTransactionType(model.type),
        amount=money(model.amount),
        lot_id=LotId(value=model.lot_id) if model.lot_id else None,
        bid_id=BidId(value=model.bid_id) if model.bid_id else None,
        created_at=to_aware_utc(model.created_at),
    )


class WalletTransactionPostgresRepository(IWalletTransactionRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert(self, entry: WalletTransaction) -> None:
        self.session.add(_to_model(entry))
        await self.session.flush()

    async def list_by_wallet(self, wallet_id: WalletId) -> list[WalletTransaction]:
        result = await self.session.execute(
            select(WalletTransactionModel)
            .where(WalletTransactionModel.wallet_id == wallet_id.value)
            .order_by(WalletTransactionModel.created_at.desc())
        )
        return [_to_entity(model) for model in result.scalars().all()]
