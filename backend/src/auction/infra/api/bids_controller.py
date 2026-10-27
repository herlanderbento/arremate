from fastapi import APIRouter, Depends, Query, status

from account.domain.user import UserId, UserRole
from auction.application.use_cases.bids.list_my_bids import (
    ListMyBidsInput,
    ListMyBidsOutput,
    ListMyBidsUseCase,
)
from auction.domain.repositories.bid_repository import IBidRepository, MyBidFilter
from auction.domain.repositories.lot_repository import ILotRepository
from auction.domain.repositories.receipt_repository import IReceiptRepository
from auction.infra.api.auction_dependencies import (
    get_bid_repository,
    get_lot_repository,
    get_receipt_repository,
)
from auction.infra.api.lot_presenters import LotPresenter
from audit.domain.hash_chain import HashChain
from audit.infra.hash_chain_provider import get_hash_chain
from shared.infra.api.auth_dependencies import AuthContext, require_role
from shared.infra.api.money import Money
from shared.infra.api.presenter import CollectionPresenter, meta_from_output

router = APIRouter(prefix="/me", tags=["My bids"])


class MyBidPresenter(LotPresenter):
    my_max_bid: Money
    my_alias: str
    situation: str
    receipt_token: str | None


class MyBidsPresenter(CollectionPresenter[MyBidPresenter]):
    @classmethod
    def from_output(cls, output: ListMyBidsOutput) -> "MyBidsPresenter":
        return cls(
            data=[
                MyBidPresenter(
                    **LotPresenter.from_output(i.lot).model_dump(),
                    my_max_bid=i.my_max_bid,
                    my_alias=i.my_alias,
                    situation=i.situation.value,
                    receipt_token=i.receipt_token,
                )
                for i in output.items
            ],
            meta=meta_from_output(output),
        )


def get_list_my_bids_use_case(
    bids: IBidRepository = Depends(get_bid_repository),
    lots: ILotRepository = Depends(get_lot_repository),
    receipts: IReceiptRepository = Depends(get_receipt_repository),
    hash_chain: HashChain = Depends(get_hash_chain),
) -> ListMyBidsUseCase:
    return ListMyBidsUseCase(bids, lots, receipts, hash_chain)


@router.get("/bids", response_model=MyBidsPresenter, status_code=status.HTTP_200_OK)
async def list_my_bids(
    filter_text: str | None = Query(default=None, max_length=100, alias="filter"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=12, ge=1, le=50),
    auth: AuthContext = Depends(require_role(UserRole.BIDDER)),
    use_case: ListMyBidsUseCase = Depends(get_list_my_bids_use_case),
):
    output = await use_case.execute(
        ListMyBidsInput(
            bidder_id=UserId(value=auth.user_id),
            page=page,
            per_page=per_page,
            filter=MyBidFilter(text=filter_text),
        )
    )
    return MyBidsPresenter.from_output(output)
