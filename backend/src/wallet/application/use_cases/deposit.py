from dataclasses import dataclass
from decimal import Decimal

from account.domain.user import UserId
from shared.application.use_cases import UseCase
from shared.domain.exceptions import NotFoundException
from wallet.application.use_cases.common.wallet_output import WalletOutput
from wallet.domain.repositories.wallet_repository import IWalletRepository
from wallet.domain.repositories.wallet_transaction_repository import (
    IWalletTransactionRepository,
)


@dataclass
class DepositInput:
    user_id: UserId
    amount: Decimal


class DepositUseCase(UseCase):
    def __init__(
        self,
        wallet_repository: IWalletRepository,
        transaction_repository: IWalletTransactionRepository,
    ):
        self.wallet_repository = wallet_repository
        self.transaction_repository = transaction_repository

    async def execute(self, input: DepositInput) -> WalletOutput:
        wallet = await self.wallet_repository.lock_by_user_id(input.user_id)
        if wallet is None:
            raise NotFoundException("Carteira não encontrada.")

        entry = wallet.deposit(input.amount)

        await self.wallet_repository.update(wallet)
        await self.transaction_repository.insert(entry)
        return WalletOutput.from_entity(wallet)
