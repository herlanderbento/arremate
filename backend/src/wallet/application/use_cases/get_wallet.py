from dataclasses import dataclass

from account.domain.user import UserId
from shared.application.use_cases import UseCase
from shared.domain.exceptions import NotFoundException
from wallet.application.use_cases.common.wallet_output import WalletOutput
from wallet.domain.repositories.wallet_repository import IWalletRepository


@dataclass
class GetWalletInput:
    user_id: UserId


class GetWalletUseCase(UseCase):
    def __init__(self, wallet_repository: IWalletRepository):
        self.wallet_repository = wallet_repository

    async def execute(self, input: GetWalletInput) -> WalletOutput:
        wallet = await self.wallet_repository.find_by_user_id(input.user_id)
        if wallet is None:
            raise NotFoundException("Carteira não encontrada.")
        return WalletOutput.from_entity(wallet)
