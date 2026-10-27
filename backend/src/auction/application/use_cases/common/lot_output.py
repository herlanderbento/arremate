from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from auction.domain.entities.lot import DisplayStatus, Lot


@dataclass(frozen=True)
class LotOutput:
    id: UUID
    title: str
    image_url: str | None
    attributes: dict[str, Any]
    status: DisplayStatus
    starting_bid: Decimal
    min_increment: Decimal
    current_bid: Decimal | None
    min_next_bid: Decimal
    bid_count: int
    starts_at: datetime
    ends_at: datetime

    @classmethod
    def from_entity(cls, lot: Lot, now: datetime) -> "LotOutput":
        return cls(
            id=lot.id.value,
            title=lot.title,
            image_url=lot.image_url,
            attributes=lot.attributes,
            status=lot.display_status(now),
            starting_bid=lot.starting_bid,
            min_increment=lot.min_increment,
            current_bid=lot.current_bid,
            min_next_bid=lot.min_next_bid(),
            bid_count=lot.bid_count,
            starts_at=lot.starts_at,
            ends_at=lot.ends_at,
        )
