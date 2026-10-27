from abc import abstractmethod

from account.domain.user import UserId
from shared.domain.repository_interface import IRepository
from wallet.domain.entities.wallet import Wallet, WalletId


class IWalletRepository(IRepository[Wallet, WalletId]):
    @abstractmethod
    async def find_by_user_id(self, user_id: UserId) -> Wallet | None:
        raise NotImplementedError()

    @abstractmethod
    async def lock_by_user_id(self, user_id: UserId) -> Wallet | None:
        raise NotImplementedError()

    @abstractmethod
    async def lock_by_user_ids(self, user_ids: set[UserId]) -> dict[UserId, Wallet]:
        raise NotImplementedError()
