from dataclasses import dataclass
from decimal import Decimal

from wallet.domain.entities.wallet import Wallet


@dataclass(frozen=True)
class WalletOutput:
    balance: Decimal
    committed: Decimal
    available: Decimal

    @classmethod
    def from_entity(cls, wallet: Wallet) -> "WalletOutput":
        return cls(
            balance=wallet.balance,
            committed=wallet.committed,
            available=wallet.available,
        )
