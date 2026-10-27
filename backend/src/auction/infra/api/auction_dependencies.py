from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from auction.application.ports.lot_room_notifier import ILotRoomNotifier
from auction.application.use_cases.bids.place_bid import PlaceBidUseCase
from auction.application.use_cases.lots.cancel_lot import CancelLotUseCase
from auction.application.use_cases.lots.create_lot import CreateLotUseCase
from auction.application.use_cases.lots.get_lot_detail import GetLotDetailUseCase
from auction.application.use_cases.lots.list_lots import ListLotsUseCase
from auction.application.use_cases.lots.list_my_lots import ListMyLotsUseCase
from auction.application.use_cases.lots.settle_lot import SettleLotInput, SettleLotUseCase
from auction.domain.entities.lot import LotId
from auction.domain.repositories.bid_repository import IBidRepository
from auction.domain.repositories.lot_repository import ILotRepository
from auction.domain.repositories.receipt_repository import IReceiptRepository
from auction.infra.composition import build_settle_lot_use_case
from auction.infra.db.bid_postgres_repository import BidPostgresRepository
from auction.infra.db.lot_postgres_repository import LotPostgresRepository
from auction.infra.db.receipt_postgres_repository import ReceiptPostgresRepository
from auction.infra.ws.connection_manager import get_lot_room_notifier
from audit.domain.hash_chain import HashChain
from audit.infra.hash_chain_provider import get_hash_chain
from catalog.domain.catalog_gateway import CatalogGateway
from catalog.infra.api.catalog_dependencies import get_catalog_gateway
from shared.application.unit_of_work import IUnitOfWork
from shared.infra.db.database import get_db_session
from shared.infra.db.unit_of_work import SqlAlchemyUnitOfWork
from wallet.domain.repositories.wallet_repository import IWalletRepository
from wallet.domain.repositories.wallet_transaction_repository import IWalletTransactionRepository
from wallet.infra.api.wallet_dependencies import (
    get_wallet_repository,
    get_wallet_transaction_repository,
)


def get_lot_repository(session: AsyncSession = Depends(get_db_session)) -> ILotRepository:
    return LotPostgresRepository(session)


def get_bid_repository(session: AsyncSession = Depends(get_db_session)) -> IBidRepository:
    return BidPostgresRepository(session)


def get_receipt_repository(
    session: AsyncSession = Depends(get_db_session),
) -> IReceiptRepository:
    return ReceiptPostgresRepository(session)


def get_unit_of_work(session: AsyncSession = Depends(get_db_session)) -> IUnitOfWork:
    return SqlAlchemyUnitOfWork(session)


def get_create_lot_use_case(
    lots: ILotRepository = Depends(get_lot_repository),
    catalog: CatalogGateway = Depends(get_catalog_gateway),
    hash_chain: HashChain = Depends(get_hash_chain),
) -> CreateLotUseCase:
    return CreateLotUseCase(lots, catalog, hash_chain)


def get_cancel_lot_use_case(
    lots: ILotRepository = Depends(get_lot_repository),
    bids: IBidRepository = Depends(get_bid_repository),
    wallets: IWalletRepository = Depends(get_wallet_repository),
    transactions: IWalletTransactionRepository = Depends(get_wallet_transaction_repository),
    unit_of_work: IUnitOfWork = Depends(get_unit_of_work),
    notifier: ILotRoomNotifier = Depends(get_lot_room_notifier),
) -> CancelLotUseCase:
    return CancelLotUseCase(lots, bids, wallets, transactions, unit_of_work, notifier)


def get_list_lots_use_case(lots: ILotRepository = Depends(get_lot_repository)) -> ListLotsUseCase:
    return ListLotsUseCase(lots)


def get_list_my_lots_use_case(
    lots: ILotRepository = Depends(get_lot_repository),
    receipts: IReceiptRepository = Depends(get_receipt_repository),
    hash_chain: HashChain = Depends(get_hash_chain),
) -> ListMyLotsUseCase:
    return ListMyLotsUseCase(lots, receipts, hash_chain)


def get_settle_lot_use_case(
    session: AsyncSession = Depends(get_db_session),
    notifier: ILotRoomNotifier = Depends(get_lot_room_notifier),
) -> SettleLotUseCase:
    return build_settle_lot_use_case(session, notifier)


def get_lot_detail_use_case(
    lots: ILotRepository = Depends(get_lot_repository),
    bids: IBidRepository = Depends(get_bid_repository),
    hash_chain: HashChain = Depends(get_hash_chain),
    settle: SettleLotUseCase = Depends(get_settle_lot_use_case),
) -> GetLotDetailUseCase:
    async def settle_lot(lot_id: LotId) -> None:
        await settle.execute(SettleLotInput(lot_id=lot_id))

    return GetLotDetailUseCase(lots, bids, hash_chain, settle_lot=settle_lot)


def get_place_bid_use_case(
    lots: ILotRepository = Depends(get_lot_repository),
    bids: IBidRepository = Depends(get_bid_repository),
    wallets: IWalletRepository = Depends(get_wallet_repository),
    transactions: IWalletTransactionRepository = Depends(get_wallet_transaction_repository),
    hash_chain: HashChain = Depends(get_hash_chain),
    unit_of_work: IUnitOfWork = Depends(get_unit_of_work),
    notifier: ILotRoomNotifier = Depends(get_lot_room_notifier),
) -> PlaceBidUseCase:
    return PlaceBidUseCase(lots, bids, wallets, transactions, hash_chain, unit_of_work, notifier)
