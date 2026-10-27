from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from account.domain.user import UserId
from auction.domain.entities.bid import Bid, BidId
from auction.domain.entities.lot import LotId
from auction.domain.repositories.bid_repository import (
    BidderLotSummary,
    IBidRepository,
    MyBidSearchInput,
    MyBidSearchOutput,
)
from auction.infra.db.sql_models import BidModel, LotModel
from shared.domain.exceptions import ConflictException
from shared.domain.money import money
from shared.utils.datetime_utils import to_aware_utc


def _title_matches(text: str):
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return LotModel.title.ilike(f"%{escaped}%", escape="\\")


def _to_model(entity: Bid) -> BidModel:
    return BidModel(
        id=entity.id.value,
        lot_id=entity.lot_id.value,
        seq=entity.seq,
        bidder_id=entity.bidder_id.value,
        amount=entity.amount,
        created_at=entity.created_at,
        prev_hash=entity.prev_hash,
        hash=entity.hash,
    )


def _to_entity(model: BidModel) -> Bid:
    return Bid(
        id=BidId(value=model.id),
        lot_id=LotId(value=model.lot_id),
        seq=model.seq,
        bidder_id=UserId(value=model.bidder_id),
        amount=money(model.amount),
        created_at=to_aware_utc(model.created_at),
        prev_hash=str(model.prev_hash).strip(),
        hash=str(model.hash).strip(),
    )


class BidPostgresRepository(IBidRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert(self, bid: Bid) -> None:
        self.session.add(_to_model(bid))
        try:
            await self.session.flush()
        except IntegrityError as exc:
            if "uq_bids_lot_seq" in str(exc.orig):
                raise ConflictException(
                    "Outro lance foi registado ao mesmo tempo. Tente de novo.", "BID_CONFLICT"
                ) from exc
            raise

    async def find_by_seq(self, lot_id: LotId, seq: int) -> Bid | None:
        result = await self.session.execute(
            select(BidModel).where(BidModel.lot_id == lot_id.value, BidModel.seq == seq)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def find_by_id(self, bid_id: BidId) -> Bid | None:
        result = await self.session.execute(select(BidModel).where(BidModel.id == bid_id.value))
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def search_by_bidder(self, props: MyBidSearchInput) -> MyBidSearchOutput:
        conditions = [BidModel.bidder_id == props.bidder_id.value]
        if props.filter and props.filter.text:
            conditions.append(_title_matches(props.filter.text))

        grouped = (
            select(
                BidModel.lot_id.label("lot_id"),
                func.max(BidModel.amount).label("max_amount"),
                func.max(BidModel.created_at).label("last_bid_at"),
            )
            .join(LotModel, LotModel.id == BidModel.lot_id)
            .where(*conditions)
            .group_by(BidModel.lot_id)
            .subquery()
        )
        total = (await self.session.execute(select(func.count()).select_from(grouped))).scalar_one()
        result = await self.session.execute(
            select(grouped.c.lot_id, grouped.c.max_amount, grouped.c.last_bid_at)
            .order_by(grouped.c.last_bid_at.desc(), grouped.c.lot_id)
            .offset((props.page - 1) * props.per_page)
            .limit(props.per_page)
        )
        return MyBidSearchOutput(
            items=[
                BidderLotSummary(
                    lot_id=LotId(value=lot_id),
                    max_amount=money(max_amount),
                    last_bid_at=to_aware_utc(last_at),
                )
                for lot_id, max_amount, last_at in result.all()
            ],
            total=total,
            current_page=props.page,
            per_page=props.per_page,
        )

    async def list_by_lot(self, lot_id: LotId) -> list[Bid]:
        result = await self.session.execute(
            select(BidModel).where(BidModel.lot_id == lot_id.value).order_by(BidModel.seq.asc())
        )
        return [_to_entity(model) for model in result.scalars().all()]
