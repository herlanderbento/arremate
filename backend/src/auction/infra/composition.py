from sqlalchemy.ext.asyncio import AsyncSession

from auction.application.ports.lot_room_notifier import ILotRoomNotifier
from auction.application.use_cases.lots.settle_lot import SettleLotUseCase
from auction.infra.db.bid_postgres_repository import BidPostgresRepository
from auction.infra.db.lot_postgres_repository import LotPostgresRepository
from auction.infra.db.receipt_postgres_repository import ReceiptPostgresRepository
from audit.infra.hash_chain_provider import get_hash_chain
from shared.infra.db.unit_of_work import SqlAlchemyUnitOfWork
from wallet.infra.db.wallet_postgres_repository import WalletPostgresRepository
from wallet.infra.db.wallet_transaction_postgres_repository import (
    WalletTransactionPostgresRepository,
)


def build_settle_lot_use_case(
    session: AsyncSession, notifier: ILotRoomNotifier
) -> SettleLotUseCase:
    return SettleLotUseCase(
        LotPostgresRepository(session),
        BidPostgresRepository(session),
        WalletPostgresRepository(session),
        WalletTransactionPostgresRepository(session),
        ReceiptPostgresRepository(session),
        get_hash_chain(),
        SqlAlchemyUnitOfWork(session),
        notifier,
    )
