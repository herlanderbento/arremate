from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from uuid import uuid4

from audit.domain.hash_chain import HashChain
from audit.domain.integrity import ChainEntry, IssueReason, LotState, ReceiptState, verify

CHAIN = HashChain("secret")
LOT = uuid4()
T0 = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)


def build(amounts: list[str]) -> tuple[LotState, list[ChainEntry]]:
    entries, prev = [], CHAIN.genesis(LOT)
    bidders = [uuid4(), uuid4()]
    for i, amount in enumerate(amounts, start=1):
        bidder, ts = bidders[i % 2], T0 + timedelta(seconds=i)
        h = CHAIN.bid_hash(prev, LOT, i, bidder, D(amount), ts)
        entries.append(ChainEntry(i, bidder, D(amount), ts, prev, h))
        prev = h
    last = entries[-1] if entries else None
    lot = LotState(
        lot_id=LOT,
        chain_head=CHAIN.chain_head(LOT, len(entries), last.hash if last else None),
        bid_count=len(entries),
        current_bid=last.amount if last else None,
        leader_id=last.bidder_id if last else None,
    )
    return lot, entries


def test_empty_and_full_histories_are_intact():
    for amounts in ([], ["1.00", "2.00", "3.00"]):
        lot, entries = build(amounts)
        report = verify(CHAIN, lot, entries, None)
        assert report.intact and report.valid_seqs == set(range(1, len(amounts) + 1))


def test_a_different_secret_flags_everything():
    lot, entries = build(["1.00", "2.00"])

    report = verify(HashChain("other"), lot, entries, None)

    assert {i.reason for i in report.issues} >= {
        IssueReason.PREV_HASH_MISMATCH,
        IssueReason.HASH_MISMATCH,
        IssueReason.CHAIN_HEAD_MISMATCH,
    }


def test_altered_bid_is_reported_once():
    lot, entries = build(["1.00", "2.00", "3.00"])
    e = entries[0]
    entries[0] = ChainEntry(e.seq, e.bidder_id, D("0.01"), e.created_at, e.prev_hash, e.hash)

    report = verify(CHAIN, lot, entries, None)

    assert [(i.reason, i.seq) for i in report.issues] == [(IssueReason.HASH_MISMATCH, 1)]
    assert report.valid_seqs == {2, 3}


def test_receipt_must_match_the_last_bid_and_head():
    lot, entries = build(["1.00", "2.00"])
    last = entries[-1]
    good = ReceiptState(lot.chain_head, D("2.00"), last.bidder_id, 2)

    assert verify(CHAIN, lot, entries, good).intact
    for bad in (
        ReceiptState("x" * 64, D("2.00"), last.bidder_id, 2),
        ReceiptState(lot.chain_head, D("1.00"), last.bidder_id, 2),
        ReceiptState(lot.chain_head, D("2.00"), uuid4(), 2),
        ReceiptState(lot.chain_head, D("2.00"), last.bidder_id, None),
    ):
        reasons = [i.reason for i in verify(CHAIN, lot, entries, bad).issues]
        assert reasons == [IssueReason.RECEIPT_MISMATCH]
