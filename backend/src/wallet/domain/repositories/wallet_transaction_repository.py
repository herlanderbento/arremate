from abc import ABC, abstractmethod

from wallet.domain.entities.wallet import WalletId
from wallet.domain.entities.wallet_transaction import WalletTransaction


class IWalletTransactionRepository(ABC):
    @abstractmethod
    async def insert(self, entry: WalletTransaction) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def list_by_wallet(self, wallet_id: WalletId) -> list[WalletTransaction]:
        raise NotImplementedError()
