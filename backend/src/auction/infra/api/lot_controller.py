from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import AwareDatetime, BaseModel, Field

from account.domain.user import UserId, UserRole
from auction.application.use_cases.bids.place_bid import PlaceBidInput, PlaceBidUseCase
from auction.application.use_cases.lots.cancel_lot import CancelLotInput, CancelLotUseCase
from auction.application.use_cases.lots.create_lot import CreateLotInput, CreateLotUseCase
from auction.application.use_cases.lots.get_lot_detail import GetLotDetailInput, GetLotDetailUseCase
from auction.application.use_cases.lots.list_lots import ListLotsInput, ListLotsUseCase
from auction.application.use_cases.lots.list_my_lots import ListMyLotsInput, ListMyLotsUseCase
from auction.domain.entities.lot import DisplayStatus, LotId
from auction.domain.repositories.lot_repository import LotFilter
from auction.infra.api.auction_dependencies import (
    get_cancel_lot_use_case,
    get_create_lot_use_case,
    get_list_lots_use_case,
    get_list_my_lots_use_case,
    get_lot_detail_use_case,
    get_place_bid_use_case,
)
from auction.infra.api.lot_presenters import (
    LotDetailPresenter,
    LotListPresenter,
    LotPresenter,
    MyLotsPresenter,
    PlaceBidPresenter,
)
from shared.infra.api.auth_dependencies import (
    AuthContext,
    optional_user,
    require_authenticated,
    require_role,
)
from shared.infra.api.money import MoneyInput, PositiveMoneyInput

router = APIRouter(prefix="/lots", tags=["Lots"])


class CreateLotRequest(BaseModel):
    external_id: str = Field(min_length=1, max_length=100)
    starting_bid: MoneyInput
    min_increment: MoneyInput
    starts_at: AwareDatetime
    ends_at: AwareDatetime


@router.post("", response_model=LotPresenter, status_code=status.HTTP_201_CREATED)
async def create_lot(
    request: CreateLotRequest,
    auth: AuthContext = Depends(require_role(UserRole.AUCTIONEER)),
    use_case: CreateLotUseCase = Depends(get_create_lot_use_case),
):
    output = await use_case.execute(
        CreateLotInput(
            auctioneer_id=UserId(value=auth.user_id),
            external_id=request.external_id.strip(),
            starting_bid=request.starting_bid,
            min_increment=request.min_increment,
            starts_at=request.starts_at,
            ends_at=request.ends_at,
        )
    )
    return LotPresenter.from_output(output)


@router.get("/mine", response_model=MyLotsPresenter, status_code=status.HTTP_200_OK)
async def list_my_lots(
    filter_text: str | None = Query(default=None, max_length=100, alias="filter"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=12, ge=1, le=50),
    sort: Literal["created_at", "ends_at", "current_bid", "title"] | None = Query(default=None),
    sort_dir: Literal["asc", "desc"] | None = Query(default=None),
    auth: AuthContext = Depends(require_role(UserRole.AUCTIONEER)),
    use_case: ListMyLotsUseCase = Depends(get_list_my_lots_use_case),
):
    output = await use_case.execute(
        ListMyLotsInput(
            auctioneer_id=UserId(value=auth.user_id),
            page=page,
            per_page=per_page,
            sort=sort,
            sort_dir=sort_dir,
            filter=LotFilter(text=filter_text),
        )
    )
    return MyLotsPresenter.from_output(output)


@router.get("", response_model=LotListPresenter, status_code=status.HTTP_200_OK)
async def list_lots(
    lot_status: Literal["live", "scheduled", "ended"] | None = Query(default=None, alias="status"),
    filter_text: str | None = Query(default=None, max_length=100, alias="filter"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=12, ge=1, le=50),
    use_case: ListLotsUseCase = Depends(get_list_lots_use_case),
):
    output = await use_case.execute(
        ListLotsInput(
            page=page,
            per_page=per_page,
            filter=LotFilter(
                status=DisplayStatus(lot_status) if lot_status else None,
                text=filter_text,
            ),
        )
    )
    return LotListPresenter.from_output(output)


@router.get("/{lot_id}", response_model=LotDetailPresenter, status_code=status.HTTP_200_OK)
async def get_lot(
    lot_id: UUID,
    auth: AuthContext | None = Depends(optional_user),
    use_case: GetLotDetailUseCase = Depends(get_lot_detail_use_case),
):
    bidder_id = UserId(value=auth.user_id) if auth and auth.user.role == UserRole.BIDDER else None
    output = await use_case.execute(
        GetLotDetailInput(lot_id=LotId(value=lot_id), bidder_id=bidder_id)
    )
    return LotDetailPresenter.from_detail(output)


@router.post("/{lot_id}/cancel", response_model=LotPresenter, status_code=status.HTTP_200_OK)
async def cancel_lot(
    lot_id: UUID,
    auth: AuthContext = Depends(require_role(UserRole.AUCTIONEER)),
    use_case: CancelLotUseCase = Depends(get_cancel_lot_use_case),
):
    output = await use_case.execute(
        CancelLotInput(lot_id=LotId(value=lot_id), auctioneer_id=UserId(value=auth.user_id))
    )
    return LotPresenter.from_output(output)


class PlaceBidRequest(BaseModel):
    amount: PositiveMoneyInput


@router.post(
    "/{lot_id}/bids", response_model=PlaceBidPresenter, status_code=status.HTTP_201_CREATED
)
async def place_bid(
    lot_id: UUID,
    request: PlaceBidRequest,
    auth: AuthContext = Depends(require_authenticated),
    use_case: PlaceBidUseCase = Depends(get_place_bid_use_case),
):
    output = await use_case.execute(
        PlaceBidInput(
            lot_id=LotId(value=lot_id),
            bidder_id=UserId(value=auth.user_id),
            bidder_role=auth.user.role,
            amount=request.amount,
        )
    )
    return PlaceBidPresenter.from_output(output)
