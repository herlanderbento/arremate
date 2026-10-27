from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.infra.db.database import get_db_session
from wallet.application.use_cases.deposit import DepositUseCase
from wallet.application.use_cases.get_wallet import GetWalletUseCase
from wallet.domain.repositories.wallet_repository import IWalletRepository
from wallet.domain.repositories.wallet_transaction_repository import (
    IWalletTransactionRepository,
)
from wallet.infra.db.wallet_postgres_repository import WalletPostgresRepository
from wallet.infra.db.wallet_transaction_postgres_repository import (
    WalletTransactionPostgresRepository,
)


def get_wallet_repository(
    session: AsyncSession = Depends(get_db_session),
) -> IWalletRepository:
    return WalletPostgresRepository(session)


def get_wallet_transaction_repository(
    session: AsyncSession = Depends(get_db_session),
) -> IWalletTransactionRepository:
    return WalletTransactionPostgresRepository(session)


def get_get_wallet_use_case(
    wallet_repo: IWalletRepository = Depends(get_wallet_repository),
) -> GetWalletUseCase:
    return GetWalletUseCase(wallet_repo)


def get_deposit_use_case(
    wallet_repo: IWalletRepository = Depends(get_wallet_repository),
    transaction_repo: IWalletTransactionRepository = Depends(get_wallet_transaction_repository),
) -> DepositUseCase:
    return DepositUseCase(wallet_repo, transaction_repo)
