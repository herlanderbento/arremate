from datetime import datetime
from typing import List, Optional, Set, Type

from sqlalchemy import and_, case, delete, extract, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from account.domain.user import UserId
from auction.domain.entities.lot import DisplayStatus, Lot, LotId, LotStatus
from auction.domain.repositories.lot_repository import (
    AuctioneerLotSearchInput,
    ILotRepository,
    LotSearchInput,
    LotSearchOutput,
)
from auction.infra.db.sql_models import LotModel
from shared.domain.money import money
from shared.domain.search_input import SortDirection
from shared.utils.datetime_utils import to_aware_utc


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return to_aware_utc(value)


def _title_matches(text: str):
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return LotModel.title.ilike(f"%{escaped}%", escape="\\")


def _to_model(entity: Lot) -> LotModel:
    return LotModel(
        id=entity.id.value,
        auctioneer_id=entity.auctioneer_id.value,
        external_id=entity.external_id,
        title=entity.title,
        image_url=entity.image_url,
        attributes=entity.attributes,
        starting_bid=entity.starting_bid,
        min_increment=entity.min_increment,
        starts_at=entity.starts_at,
        ends_at=entity.ends_at,
        status=entity.status.value,
        current_bid=entity.current_bid,
        leader_id=entity.leader_id.value if entity.leader_id else None,
        bid_count=entity.bid_count,
        chain_head=entity.chain_head,
        created_at=entity.created_at,
        cancelled_at=entity.cancelled_at,
        settled_at=entity.settled_at,
    )


def _to_entity(model: LotModel) -> Lot:
    return Lot(
        id=LotId(value=model.id),
        auctioneer_id=UserId(value=model.auctioneer_id),
        external_id=model.external_id,
        title=model.title,
        image_url=model.image_url,
        attributes=dict(model.attributes or {}),
        starting_bid=money(model.starting_bid),
        min_increment=money(model.min_increment),
        starts_at=to_aware_utc(model.starts_at),
        ends_at=to_aware_utc(model.ends_at),
        status=LotStatus(model.status),
        current_bid=(money(model.current_bid) if model.current_bid is not None else None),
        leader_id=UserId(value=model.leader_id) if model.leader_id else None,
        bid_count=model.bid_count,
        chain_head=str(model.chain_head).strip(),
        created_at=to_aware_utc(model.created_at),
        cancelled_at=_aware(model.cancelled_at),
        settled_at=_aware(model.settled_at),
    )


class LotPostgresRepository(ILotRepository):
    sortable_fields = ["ends_at", "starts_at", "current_bid", "title", "created_at"]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert(self, entity: Lot) -> None:
        self.session.add(_to_model(entity))
        await self.session.flush()

    async def bulk_insert(self, entities: List[Lot]) -> None:
        self.session.add_all([_to_model(entity) for entity in entities])
        await self.session.flush()

    async def find_by_id(self, entity_id: LotId) -> Optional[Lot]:
        result = await self.session.execute(
            select(LotModel)
            .where(LotModel.id == entity_id.value)
            .execution_options(populate_existing=True)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def find_all(self) -> List[Lot]:
        result = await self.session.execute(select(LotModel))
        return [_to_entity(model) for model in result.scalars().all()]

    async def find_by_ids(self, entity_ids: Set[LotId]) -> List[Lot]:
        raw_ids = [entity_id.value for entity_id in entity_ids]
        result = await self.session.execute(select(LotModel).where(LotModel.id.in_(raw_ids)))
        return [_to_entity(model) for model in result.scalars().all()]

    async def update(self, entity: Lot) -> None:
        await self.session.execute(
            update(LotModel)
            .where(LotModel.id == entity.id.value)
            .values(
                external_id=entity.external_id,
                title=entity.title,
                image_url=entity.image_url,
                attributes=entity.attributes,
                starting_bid=entity.starting_bid,
                min_increment=entity.min_increment,
                starts_at=entity.starts_at,
                ends_at=entity.ends_at,
                status=entity.status.value,
                current_bid=entity.current_bid,
                leader_id=entity.leader_id.value if entity.leader_id else None,
                bid_count=entity.bid_count,
                chain_head=entity.chain_head,
                cancelled_at=entity.cancelled_at,
                settled_at=entity.settled_at,
            )
        )

    async def delete(self, entity_id: LotId) -> None:
        await self.session.execute(delete(LotModel).where(LotModel.id == entity_id.value))

    async def search(self, props: LotSearchInput) -> LotSearchOutput:
        now = props.now
        status = props.filter.status if props.filter else None
        text = props.filter.text if props.filter else None

        active = LotModel.status == LotStatus.ACTIVE.value
        live = and_(active, LotModel.starts_at <= now, LotModel.ends_at > now)
        scheduled = and_(active, LotModel.starts_at > now)
        ended = or_(
            LotModel.status == LotStatus.SETTLED.value, and_(active, LotModel.ends_at <= now)
        )

        conditions = [LotModel.status != LotStatus.CANCELLED.value]
        if status == DisplayStatus.LIVE:
            conditions.append(live)
        elif status == DisplayStatus.SCHEDULED:
            conditions.append(scheduled)
        elif status == DisplayStatus.ENDED:
            conditions.append(ended)
        if text:
            conditions.append(_title_matches(text))

        group = case((live, 0), (scheduled, 1), else_=2)
        within = case(
            (live, extract("epoch", LotModel.ends_at)),
            (scheduled, extract("epoch", LotModel.starts_at)),
            else_=-extract("epoch", LotModel.ends_at),
        )

        total = (
            await self.session.execute(
                select(func.count()).select_from(LotModel).where(*conditions)
            )
        ).scalar_one()

        query = select(LotModel).where(*conditions)
        if props.sort and props.sort in self.sortable_fields:
            column = getattr(LotModel, props.sort)
            ordering = column.desc() if props.sort_dir == SortDirection.DESC else column.asc()
            query = query.order_by(ordering, LotModel.id)
        else:
            query = query.order_by(group, within, LotModel.id)

        result = await self.session.execute(
            query.offset((props.page - 1) * props.per_page).limit(props.per_page)
        )
        return LotSearchOutput(
            items=[_to_entity(m) for m in result.scalars().all()],
            total=total,
            current_page=props.page,
            per_page=props.per_page,
        )

    async def search_by_auctioneer(self, props: AuctioneerLotSearchInput) -> LotSearchOutput:
        conditions = [LotModel.auctioneer_id == props.auctioneer_id.value]
        if props.filter and props.filter.text:
            conditions.append(_title_matches(props.filter.text))

        total = (
            await self.session.execute(
                select(func.count()).select_from(LotModel).where(*conditions)
            )
        ).scalar_one()

        query = select(LotModel).where(*conditions)
        if props.sort and props.sort in self.sortable_fields:
            column = getattr(LotModel, props.sort)
            ordering = column.desc() if props.sort_dir == SortDirection.DESC else column.asc()
            query = query.order_by(ordering, LotModel.id)
        else:
            query = query.order_by(LotModel.created_at.desc(), LotModel.id)

        result = await self.session.execute(
            query.offset((props.page - 1) * props.per_page).limit(props.per_page)
        )
        return LotSearchOutput(
            items=[_to_entity(m) for m in result.scalars().all()],
            total=total,
            current_page=props.page,
            per_page=props.per_page,
        )

    async def list_due_for_settlement(self, now: datetime, limit: int) -> list[LotId]:
        result = await self.session.execute(
            select(LotModel.id)
            .where(LotModel.status == LotStatus.ACTIVE.value, LotModel.ends_at <= now)
            .order_by(LotModel.ends_at)
            .limit(limit)
        )
        return [LotId(value=lot_id) for lot_id in result.scalars().all()]

    async def lock_by_id(self, lot_id: LotId) -> Lot | None:
        result = await self.session.execute(
            select(LotModel)
            .where(LotModel.id == lot_id.value)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    def get_entity(self) -> Type[Lot]:
        return Lot
