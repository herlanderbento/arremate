from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any

from account.domain.user import UserId
from shared.domain.entity import AggregateRoot
from shared.domain.exceptions import DomainError
from shared.domain.money import format_brl, money
from shared.domain.value_objects import Uuid

ANTI_SNIPE_WINDOW = timedelta(minutes=2)
ANTI_SNIPE_EXTENSION = timedelta(minutes=2)


def _amount(value: Decimal) -> Decimal:
    try:
        return money(value)
    except ValueError as exc:
        raise DomainError(
            "INVALID_AMOUNT", "Valor inválido (use até duas casas decimais)."
        ) from exc


class LotStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"
    SETTLED = "SETTLED"


class DisplayStatus(str, Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    ENDED = "ended"
    CANCELLED = "cancelled"


class LotId(Uuid):
    pass


@dataclass(frozen=True, slots=True)
class BidOutcome:
    previous_leader_id: UserId | None
    previous_amount: Decimal | None
    extended: bool


@dataclass(slots=True, kw_only=True)
class Lot(AggregateRoot):
    id: LotId = field(default_factory=LotId)
    auctioneer_id: UserId
    external_id: str
    title: str
    image_url: str | None
    attributes: dict[str, Any] = field(default_factory=dict)
    starting_bid: Decimal
    min_increment: Decimal
    starts_at: datetime
    ends_at: datetime
    status: LotStatus = LotStatus.ACTIVE
    current_bid: Decimal | None = None
    leader_id: UserId | None = None
    bid_count: int = 0
    chain_head: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    cancelled_at: datetime | None = None
    settled_at: datetime | None = None

    @property
    def entity_id(self) -> LotId:
        return self.id

    @staticmethod
    def create(
        *,
        id: LotId,
        auctioneer_id: UserId,
        external_id: str,
        title: str,
        image_url: str | None,
        attributes: dict[str, Any],
        starting_bid: Decimal,
        min_increment: Decimal,
        starts_at: datetime,
        ends_at: datetime,
        chain_head: str,
        now: datetime,
    ) -> "Lot":
        starting_bid, min_increment = _amount(starting_bid), _amount(min_increment)
        if starting_bid <= 0 or min_increment <= 0:
            raise DomainError(
                "INVALID_AMOUNT", "O lance inicial e o incremento mínimo devem ser positivos."
            )
        if ends_at <= starts_at:
            raise DomainError("INVALID_SCHEDULE", "O fim do lote deve ser depois do início.")
        if ends_at <= now:
            raise DomainError("INVALID_SCHEDULE", "O fim do lote deve estar no futuro.")
        return Lot(
            id=id,
            auctioneer_id=auctioneer_id,
            external_id=external_id,
            title=title,
            image_url=image_url,
            attributes=attributes,
            starting_bid=starting_bid,
            min_increment=min_increment,
            starts_at=starts_at,
            ends_at=ends_at,
            chain_head=chain_head,
            created_at=now,
        )

    def display_status(self, now: datetime) -> DisplayStatus:
        if self.status == LotStatus.CANCELLED:
            return DisplayStatus.CANCELLED
        if self.status == LotStatus.SETTLED or now >= self.ends_at:
            return DisplayStatus.ENDED
        if now < self.starts_at:
            return DisplayStatus.SCHEDULED
        return DisplayStatus.LIVE

    def min_next_bid(self) -> Decimal:
        if self.bid_count == 0 or self.current_bid is None:
            return self.starting_bid
        return self.current_bid + self.min_increment

    def is_due_for_settlement(self, now: datetime) -> bool:
        return self.status == LotStatus.ACTIVE and now >= self.ends_at

    def check_bid(self, bidder_id: UserId, amount: Decimal, now: datetime) -> None:
        amount = _amount(amount)

        if self.status != LotStatus.ACTIVE or now >= self.ends_at:
            raise DomainError("LOT_ENDED", "Este lote já foi encerrado.")
        if now < self.starts_at:
            raise DomainError("LOT_NOT_STARTED", "Este lote ainda não começou.")
        if self.leader_id == bidder_id:
            raise DomainError("ALREADY_WINNING", "Você já está ganhando este lote.")
        minimum = self.min_next_bid()
        if amount < minimum:
            raise DomainError(
                "BELOW_MINIMUM",
                f"O lance mínimo é {format_brl(minimum)}.",
                {"min_amount": minimum},
            )

    def apply_bid(
        self, bidder_id: UserId, amount: Decimal, now: datetime, chain_head: str
    ) -> BidOutcome:
        self.check_bid(bidder_id, amount, now)
        amount = money(amount)
        outcome_leader, outcome_amount = self.leader_id, self.current_bid

        extended = self.ends_at - now <= ANTI_SNIPE_WINDOW
        if extended:
            self.ends_at = now + ANTI_SNIPE_EXTENSION
        self.current_bid = amount
        self.leader_id = bidder_id
        self.bid_count += 1
        self.chain_head = chain_head
        return BidOutcome(outcome_leader, outcome_amount, extended)

    def cancel(self, now: datetime, allow_with_bids: bool = False) -> None:
        if self.status != LotStatus.ACTIVE or now >= self.ends_at:
            raise DomainError(
                "LOT_NOT_CANCELLABLE", "Só é possível cancelar lotes agendados ou ao vivo."
            )
        if self.bid_count > 0 and not allow_with_bids:
            raise DomainError("LOT_HAS_BIDS", "Não é possível cancelar um lote com lances.")
        self.status = LotStatus.CANCELLED
        self.cancelled_at = now

    def mark_settled(self, now: datetime) -> None:
        if not self.is_due_for_settlement(now):
            raise DomainError("LOT_NOT_SETTLEABLE", "O lote ainda não pode ser liquidado.")
        self.status = LotStatus.SETTLED
        self.settled_at = now
