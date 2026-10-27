from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from auction.application.use_cases.bids.place_bid import PlaceBidOutput
from auction.application.use_cases.common.lot_output import LotOutput
from auction.application.use_cases.lots.get_lot_detail import LotDetailOutput
from auction.application.use_cases.lots.list_lots import ListLotsOutput
from auction.application.use_cases.lots.list_my_lots import ListMyLotsOutput
from shared.infra.api.money import Money
from shared.infra.api.presenter import CollectionPresenter, meta_from_output


class LotPresenter(BaseModel):
    id: UUID
    title: str
    image_url: str | None
    attributes: dict[str, Any]
    status: str
    starting_bid: Money
    min_increment: Money
    current_bid: Money | None
    min_next_bid: Money
    bid_count: int
    starts_at: datetime
    ends_at: datetime

    @classmethod
    def from_output(cls, o: LotOutput) -> "LotPresenter":
        return cls(
            id=o.id,
            title=o.title,
            image_url=o.image_url,
            attributes=o.attributes,
            status=o.status.value,
            starting_bid=o.starting_bid,
            min_increment=o.min_increment,
            current_bid=o.current_bid,
            min_next_bid=o.min_next_bid,
            bid_count=o.bid_count,
            starts_at=o.starts_at,
            ends_at=o.ends_at,
        )


class LotListPresenter(CollectionPresenter[LotPresenter]):
    @classmethod
    def from_output(cls, o: ListLotsOutput) -> "LotListPresenter":
        return cls(
            data=[LotPresenter.from_output(i) for i in o.items],
            meta=meta_from_output(o),
        )


class LotResultPresenter(BaseModel):
    sold: bool
    final_amount: Money | None
    winner_alias: str | None


class MyLotPresenter(LotPresenter):
    result: LotResultPresenter


class MyLotsPresenter(CollectionPresenter[MyLotPresenter]):
    total_received: Money

    @classmethod
    def from_output(cls, o: ListMyLotsOutput) -> "MyLotsPresenter":
        return cls(
            data=[
                MyLotPresenter(
                    **LotPresenter.from_output(i.lot).model_dump(),
                    result=LotResultPresenter(
                        sold=i.sold,
                        final_amount=i.final_amount,
                        winner_alias=i.winner_alias,
                    ),
                )
                for i in o.items
            ],
            meta=meta_from_output(o),
            total_received=o.total_received,
        )


class BidHistoryPresenter(BaseModel):
    seq: int
    bidder_alias: str
    amount: Money
    created_at: datetime


class LotDetailPresenter(LotPresenter):
    server_time: datetime
    leader_alias: str | None
    my_alias: str | None
    bids: list[BidHistoryPresenter]

    @classmethod
    def from_detail(cls, o: LotDetailOutput) -> "LotDetailPresenter":
        return cls(
            **LotPresenter.from_output(o.lot).model_dump(),
            server_time=o.server_time,
            leader_alias=o.leader_alias,
            my_alias=o.my_alias,
            bids=[
                BidHistoryPresenter(
                    seq=b.seq,
                    bidder_alias=b.bidder_alias,
                    amount=b.amount,
                    created_at=b.created_at,
                )
                for b in o.bids
            ],
        )


class PlaceBidPresenter(BaseModel):
    seq: int
    amount: Money
    bidder_alias: str
    created_at: datetime
    ends_at: datetime
    extended: bool
    min_next_bid: Money
    bid_count: int
    available: Money

    @classmethod
    def from_output(cls, o: PlaceBidOutput) -> "PlaceBidPresenter":
        return cls(**o.__dict__)
