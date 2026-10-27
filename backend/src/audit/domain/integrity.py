from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from audit.domain.hash_chain import HashChain


class IssueReason(str, Enum):
    SEQ_GAP = "SEQ_GAP"
    PREV_HASH_MISMATCH = "PREV_HASH_MISMATCH"
    HASH_MISMATCH = "HASH_MISMATCH"
    CHAIN_HEAD_MISMATCH = "CHAIN_HEAD_MISMATCH"
    LOT_STATE_MISMATCH = "LOT_STATE_MISMATCH"
    RECEIPT_MISMATCH = "RECEIPT_MISMATCH"


@dataclass(frozen=True, slots=True)
class ChainEntry:
    seq: int
    bidder_id: UUID
    amount: Decimal
    created_at: datetime
    prev_hash: str
    hash: str


@dataclass(frozen=True, slots=True)
class LotState:
    lot_id: UUID
    chain_head: str
    bid_count: int
    current_bid: Decimal | None
    leader_id: UUID | None


@dataclass(frozen=True, slots=True)
class ReceiptState:
    chain_head: str
    amount: Decimal
    winner_id: UUID
    winning_bid_seq: int | None  # None when the winning bid row no longer exists


@dataclass(frozen=True, slots=True)
class Issue:
    reason: IssueReason
    seq: int | None = None


@dataclass(slots=True)
class IntegrityReport:
    issues: list[Issue] = field(default_factory=list)
    valid_seqs: set[int] = field(default_factory=set)

    @property
    def intact(self) -> bool:
        return not self.issues


def verify(
    chain: HashChain,
    lot: LotState,
    entries: list[ChainEntry],
    receipt: ReceiptState | None,
) -> IntegrityReport:
    report = IntegrityReport()
    entries = sorted(entries, key=lambda e: e.seq)

    expected_prev = chain.genesis(lot.lot_id)
    for position, entry in enumerate(entries, start=1):
        ok = True
        if entry.seq != position:
            report.issues.append(Issue(IssueReason.SEQ_GAP, entry.seq))
            ok = False
        if not chain.same(entry.prev_hash, expected_prev):
            report.issues.append(Issue(IssueReason.PREV_HASH_MISMATCH, entry.seq))
            ok = False
        recomputed = chain.bid_hash(
            entry.prev_hash,
            lot.lot_id,
            entry.seq,
            entry.bidder_id,
            entry.amount,
            entry.created_at,
        )
        if not chain.same(entry.hash, recomputed):
            report.issues.append(Issue(IssueReason.HASH_MISMATCH, entry.seq))
            ok = False
        if ok:
            report.valid_seqs.add(entry.seq)
        # Follow the stored hash so one altered bid is reported once, not on every later bid.
        expected_prev = entry.hash

    last = entries[-1] if entries else None
    expected_head = chain.chain_head(lot.lot_id, len(entries), last.hash if last else None)
    if not chain.same(lot.chain_head, expected_head):
        report.issues.append(Issue(IssueReason.CHAIN_HEAD_MISMATCH))

    if (
        lot.bid_count != len(entries)
        or lot.current_bid != (last.amount if last else None)
        or lot.leader_id != (last.bidder_id if last else None)
    ):
        report.issues.append(Issue(IssueReason.LOT_STATE_MISMATCH))

    if receipt is not None and (
        not chain.same(receipt.chain_head, lot.chain_head)
        or last is None
        or receipt.winning_bid_seq != last.seq
        or receipt.amount != last.amount
        or receipt.winner_id != last.bidder_id
    ):
        report.issues.append(Issue(IssueReason.RECEIPT_MISMATCH))

    return report
