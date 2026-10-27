from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from account.domain.user import UserId
from auction.domain.entities.bid import BidId
from auction.domain.entities.lot import LotId
from shared.domain.entity import AggregateRoot
from shared.domain.value_objects import Uuid


class ReceiptId(Uuid):
    pass


@dataclass(slots=True, kw_only=True)
class Receipt(AggregateRoot):
    id: ReceiptId = field(default_factory=ReceiptId)
    lot_id: LotId
    winner_id: UserId
    winning_bid_id: BidId | None
    amount: Decimal
    chain_head: str
    public_token: str
    issued_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def entity_id(self) -> ReceiptId:
        return self.id
