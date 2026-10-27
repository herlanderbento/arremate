from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from account.domain.user import UserId, UserRole
from shared.infra.api.auth_dependencies import AuthContext, require_role
from shared.infra.api.money import MoneyInput
from wallet.application.use_cases.deposit import DepositInput, DepositUseCase
from wallet.application.use_cases.get_wallet import GetWalletInput, GetWalletUseCase
from wallet.infra.api.wallet_dependencies import (
    get_deposit_use_case,
    get_get_wallet_use_case,
)
from wallet.infra.api.wallet_presenter import WalletPresenter

router = APIRouter(prefix="/wallet", tags=["Wallet"])


class DepositRequest(BaseModel):
    amount: MoneyInput


@router.get("", response_model=WalletPresenter, status_code=status.HTTP_200_OK)
async def get_wallet(
    auth: AuthContext = Depends(require_role(UserRole.BIDDER)),
    use_case: GetWalletUseCase = Depends(get_get_wallet_use_case),
):
    output = await use_case.execute(GetWalletInput(user_id=UserId(value=auth.user_id)))
    return WalletPresenter.from_output(output)


@router.post("/deposit", response_model=WalletPresenter, status_code=status.HTTP_200_OK)
async def deposit(
    request: DepositRequest,
    auth: AuthContext = Depends(require_role(UserRole.BIDDER)),
    use_case: DepositUseCase = Depends(get_deposit_use_case),
):
    output = await use_case.execute(
        DepositInput(user_id=UserId(value=auth.user_id), amount=request.amount)
    )
    return WalletPresenter.from_output(output)
