from pydantic import BaseModel

from shared.infra.api.money import Money
from wallet.application.use_cases.common.wallet_output import WalletOutput


class WalletPresenter(BaseModel):
    balance: Money
    committed: Money
    available: Money

    @classmethod
    def from_output(cls, output: WalletOutput) -> "WalletPresenter":
        return cls(
            balance=output.balance,
            committed=output.committed,
            available=output.available,
        )
