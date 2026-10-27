import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest
from sqlalchemy import select

from auction.infra.db.sql_models import BidModel, LotModel
from audit.infra.hash_chain_provider import get_hash_chain
from tests.helpers import (
    at,
    bid,
    create_lot,
    deposit,
    register_and_login,
    set_lot_times,
    wallet,
)
from tests.integration.conftest import new_client
from wallet.infra.db.sql_models import WalletTransactionModel


@pytest.fixture
async def auction(client):
    await register_and_login(client, "boss@example.com", "AUCTIONEER")
    lot = await create_lot(client, starting_bid="100.00", min_increment="5.00")
    ana, bia = new_client(), new_client()
    await register_and_login(ana, "ana@example.com")
    await register_and_login(bia, "bia@example.com")
    await deposit(ana, "1000.00")
    await deposit(bia, "1000.00")
    yield lot, ana, bia
    await ana.aclose()
    await bia.aclose()


def _error(response):
    return response.status_code, response.json()["error"]["code"]


async def test_first_bid_commits_balance_and_is_announced(auction, notifier, db_session):
    lot, ana, _ = auction

    response = await bid(ana, lot["id"], "120.00")

    assert response.status_code == 201
    body = response.json()
    assert (body["seq"], body["amount"], body["bid_count"]) == (1, "120.00", 1)
    assert body["min_next_bid"] == "125.00"
    assert body["available"] == "880.00"
    assert await wallet(ana) == {
        "balance": "1000.00",
        "committed": "120.00",
        "available": "880.00",
    }
    my_alias = (await ana.get(f"/lots/{lot['id']}")).json()["my_alias"]
    assert body["bidder_alias"] == my_alias

    [(lot_id, event)] = notifier.events
    assert str(lot_id) == lot["id"]
    assert event["type"] == "bid_placed"
    assert event["bidder_alias"] == my_alias
    assert not {"bidder_id", "user_id", "email", "name"} & set(event)

    holds = (await db_session.execute(select(WalletTransactionModel))).scalars().all()
    assert [(t.type, t.amount) for t in holds if t.type != "DEPOSIT"] == [("HOLD", D("120.00"))]


async def test_outbid_bidder_gets_balance_back_immediately(auction, db_session):
    lot, ana, bia = auction
    await bid(ana, lot["id"], "100.00")

    response = await bid(bia, lot["id"], "105.00")

    assert response.status_code == 201
    assert (await wallet(ana))["available"] == "1000.00"
    assert (await wallet(bia))["committed"] == "105.00"
    entries = (await db_session.execute(select(WalletTransactionModel))).scalars().all()
    assert sorted((t.type, t.amount) for t in entries if t.type != "DEPOSIT") == [
        ("HOLD", D("100.00")),
        ("HOLD", D("105.00")),
        ("RELEASE", D("100.00")),
    ]
    detail = (await ana.get(f"/lots/{lot['id']}")).json()
    assert detail["leader_alias"] != detail["my_alias"]
    assert [b["amount"] for b in detail["bids"]] == ["105.00", "100.00"]


async def test_refusal_codes(auction, client):
    lot, ana, bia = auction

    below = await bid(ana, lot["id"], "99.99")
    assert _error(below) == (422, "BELOW_MINIMUM")
    assert below.json()["error"]["details"] == {"min_amount": "100.00"}
    assert below.json()["error"]["message"] == "O lance mínimo é R$ 100,00."

    assert (await bid(ana, lot["id"], "100.00")).status_code == 201
    assert _error(await bid(ana, lot["id"], "200.00")) == (422, "ALREADY_WINNING")
    assert _error(await bid(bia, lot["id"], "104.99")) == (422, "BELOW_MINIMUM")

    poor = await bid(bia, lot["id"], "1000.01")
    assert _error(poor) == (422, "INSUFFICIENT_BALANCE")
    assert poor.json()["error"]["details"] == {"available": "1000.00"}

    assert _error(await bid(client, lot["id"], "500.00")) == (403, "AUCTIONEER_CANNOT_BID")

    scheduled = await create_lot(client, starts_at=at(hours=1), ends_at=at(hours=2))
    assert _error(await bid(ana, scheduled["id"], "100.00")) == (422, "LOT_NOT_STARTED")

    await set_lot_times(lot["id"], ends_at=datetime.now(UTC) - timedelta(seconds=1))
    assert _error(await bid(bia, lot["id"], "500.00")) == (422, "LOT_ENDED")

    missing = await bid(ana, "00000000-0000-0000-0000-000000000000", "100.00")
    assert missing.status_code == 404
    assert (await wallet(bia))["committed"] == "0.00"  # refused bids hold nothing


async def test_balance_committed_in_one_lot_is_not_available_in_another(auction, client):
    lot, ana, _ = auction
    other = await create_lot(client)
    assert (await bid(ana, lot["id"], "600.00")).status_code == 201

    response = await bid(ana, other["id"], "500.00")

    assert _error(response) == (422, "INSUFFICIENT_BALANCE")
    assert response.json()["error"]["details"] == {"available": "400.00"}


async def test_bids_must_be_positive_with_two_decimals(auction):
    lot, ana, _ = auction

    for amount in (0, "0.00", "-100.00", "100.001", 100.001, "cem", None, "Infinity"):
        response = await ana.post(f"/lots/{lot['id']}/bids", json={"amount": amount})
        assert _error(response) == (422, "VALIDATION_ERROR"), amount


async def test_anti_sniping_extends_to_now_plus_two_minutes(auction, notifier):
    lot, ana, _ = auction
    await set_lot_times(lot["id"], ends_at=datetime.now(UTC) + timedelta(seconds=30))

    before = datetime.now(UTC)
    response = await bid(ana, lot["id"], "100.00")

    body = response.json()
    assert body["extended"] is True
    new_end = datetime.fromisoformat(body["ends_at"])
    assert before + timedelta(minutes=2) <= new_end <= datetime.now(UTC) + timedelta(minutes=2)
    assert notifier.types() == ["bid_placed", "lot_extended"]


async def test_bid_far_from_the_end_does_not_extend(auction, notifier):
    lot, ana, _ = auction

    body = (await bid(ana, lot["id"], "100.00")).json()

    assert body["extended"] is False
    assert datetime.fromisoformat(body["ends_at"]) == datetime.fromisoformat(lot["ends_at"])
    assert notifier.types() == ["bid_placed"]


async def test_bids_are_hash_chained(auction, db_session):
    lot, ana, bia = auction
    for client, amount in ((ana, "100.00"), (bia, "105.00"), (ana, "110.00")):
        assert (await bid(client, lot["id"], amount)).status_code == 201

    chain = get_hash_chain()
    bids = (await db_session.execute(select(BidModel).order_by(BidModel.seq))).scalars().all()
    lot_row = (await db_session.execute(select(LotModel))).scalar_one()

    assert [b.seq for b in bids] == [1, 2, 3]
    assert bids[0].prev_hash == chain.genesis(lot_row.id)
    for previous, current in zip(bids, bids[1:]):
        assert current.prev_hash == previous.hash
    for b in bids:
        assert b.hash == chain.bid_hash(
            b.prev_hash, b.lot_id, b.seq, b.bidder_id, b.amount, b.created_at
        )
    assert lot_row.chain_head == chain.chain_head(lot_row.id, 3, bids[-1].hash)


async def test_simultaneous_bids_only_one_wins(auction, db_session):
    lot, ana, bia = auction

    responses = await asyncio.gather(bid(ana, lot["id"], "100.00"), bid(bia, lot["id"], "100.00"))

    assert sorted(r.status_code for r in responses) == [201, 422]
    loser = next(r for r in responses if r.status_code == 422)
    assert loser.json()["error"]["code"] == "BELOW_MINIMUM"
    committed = sorted([(await wallet(ana))["committed"], (await wallet(bia))["committed"]])
    assert committed == ["0.00", "100.00"]
    assert len((await db_session.execute(select(BidModel))).scalars().all()) == 1


async def test_bidding_war_keeps_wallets_consistent(client, db_session):
    await register_and_login(client, "boss@example.com", "AUCTIONEER")
    lot = await create_lot(client, starting_bid="10.00", min_increment="1.00")
    bidders = [new_client() for _ in range(6)]
    for i, c in enumerate(bidders):
        await register_and_login(c, f"b{i}@example.com")
        await deposit(c, "10000.00")

    for round_ in range(3):
        await asyncio.gather(
            *(bid(c, lot["id"], f"{10 + 10 * (round_ * 6 + i)}.00") for i, c in enumerate(bidders))
        )

    lot_row = (await db_session.execute(select(LotModel))).scalar_one()
    seqs = (await db_session.execute(select(BidModel.seq).order_by(BidModel.seq))).scalars().all()
    wallets = [await wallet(c) for c in bidders]
    for c in bidders:
        await c.aclose()

    assert seqs == list(range(1, lot_row.bid_count + 1))
    # Only the leader has money committed, and exactly the winning amount.
    assert sum(D(w["committed"]) for w in wallets) == lot_row.current_bid
    assert sorted(D(w["committed"]) > 0 for w in wallets) == [False] * 5 + [True]
    assert all(w["balance"] == "10000.00" for w in wallets)


async def test_crossed_bids_on_two_lots_do_not_deadlock(auction, client):
    lot_a, ana, bia = auction
    lot_b = await create_lot(client)
    await bid(ana, lot_a["id"], "100.00")
    await bid(bia, lot_b["id"], "100.00")

    responses = await asyncio.wait_for(
        asyncio.gather(bid(ana, lot_b["id"], "200.00"), bid(bia, lot_a["id"], "200.00")), timeout=10
    )

    assert [r.status_code for r in responses] == [201, 201]
    assert (await wallet(ana))["committed"] == "200.00"
    assert (await wallet(bia))["committed"] == "200.00"
