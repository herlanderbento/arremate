from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from account.domain.user import UserId
from auction.domain.entities.lot import LotId
from shared.domain.entity import AggregateRoot
from shared.domain.value_objects import Uuid


class BidId(Uuid):
    pass


@dataclass(slots=True, kw_only=True)
class Bid(AggregateRoot):
    id: BidId = field(default_factory=BidId)
    lot_id: LotId
    seq: int
    bidder_id: UserId
    amount: Decimal
    created_at: datetime
    prev_hash: str
    hash: str

    @property
    def entity_id(self) -> BidId:
        return self.id
