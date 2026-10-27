from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal as D
from uuid import uuid4

import pytest

from audit.domain.hash_chain import HashChain, canonical_ts

LOT, USER = uuid4(), uuid4()
TS = datetime(2026, 10, 25, 12, 0, 0, 123456, tzinfo=UTC)


def test_canonical_ts_is_utc_with_microseconds():
    same_instant = TS.astimezone(timezone(timedelta(hours=-3)))

    assert canonical_ts(TS) == "2026-10-25T12:00:00.123456Z"
    assert canonical_ts(same_instant) == canonical_ts(TS)
    with pytest.raises(ValueError):
        canonical_ts(TS.replace(tzinfo=None))


def test_hashes_depend_on_the_secret():
    a, b = HashChain("secret-a"), HashChain("secret-b")

    assert a.genesis(LOT) != b.genesis(LOT)
    assert a.chain_head(LOT, 0, None) != b.chain_head(LOT, 0, None)
    assert len(a.genesis(LOT)) == 64


def test_bid_hash_covers_every_field():
    chain = HashChain("s")
    base = dict(prev_hash="p", lot_id=LOT, seq=1, bidder_id=USER, amount=D("1.00"), created_at=TS)
    reference = chain.bid_hash(**base)
    variations = [
        {"prev_hash": "q"},
        {"lot_id": uuid4()},
        {"seq": 2},
        {"bidder_id": uuid4()},
        {"amount": D("1.01")},
        {"created_at": TS + timedelta(microseconds=1)},
    ]

    for change in variations:
        assert chain.bid_hash(**{**base, **change}) != reference, change


def test_chain_head_binds_count_and_last_hash():
    chain = HashChain("s")

    empty = chain.chain_head(LOT, 0, None)
    assert empty == chain.chain_head(LOT, 0, chain.genesis(LOT))
    assert chain.chain_head(LOT, 1, "h1") != chain.chain_head(LOT, 2, "h1")
    assert chain.chain_head(LOT, 1, "h1") != chain.chain_head(LOT, 1, "h2")


def test_alias_is_stable_per_lot_and_differs_between_lots():
    chain = HashChain("s")

    alias = chain.alias(USER, LOT)
    assert alias == chain.alias(USER, LOT)
    assert alias.startswith("Licitante ") and len(alias) == len("Licitante ") + 8
    assert alias != chain.alias(USER, uuid4())
    assert str(USER) not in alias


def test_amount_enters_the_hash_in_canonical_form():
    """Decimal('1') and Decimal('1.00') are the same money and must give the same hash, so a
    value read back from NUMERIC(14,2) always matches the one hashed when the bid was made."""
    chain = HashChain("s")
    args = dict(prev_hash="p", lot_id=LOT, seq=1, bidder_id=USER, created_at=TS)

    assert chain.bid_hash(**args, amount=D("1")) == chain.bid_hash(**args, amount=D("1.00"))
    assert chain.bid_hash(**args, amount=D("1.00")) != chain.bid_hash(**args, amount=D("1.01"))
