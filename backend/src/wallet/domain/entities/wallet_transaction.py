from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from auction.domain.entities.bid import BidId
from auction.domain.entities.lot import LotId
from shared.domain.entity import AggregateRoot
from shared.domain.value_objects import Uuid

if TYPE_CHECKING:
    from wallet.domain.entities.wallet import WalletId


class WalletTransactionType(str, Enum):
    DEPOSIT = "DEPOSIT"
    HOLD = "HOLD"
    RELEASE = "RELEASE"
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class WalletTransactionId(Uuid):
    pass


@dataclass(slots=True, kw_only=True)
class WalletTransaction(AggregateRoot):
    id: WalletTransactionId = field(default_factory=WalletTransactionId)
    wallet_id: WalletId
    type: WalletTransactionType
    amount: Decimal
    lot_id: LotId | None = None
    bid_id: BidId | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def entity_id(self) -> WalletTransactionId:
        return self.id
