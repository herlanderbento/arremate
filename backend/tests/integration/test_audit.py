from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from auction.infra.worker.settlement_worker import settle_due_lots
from shared.infra.db.database import AsyncSessionLocal
from tests.fakes.notifier import RecordingNotifier
from tests.helpers import bid, create_lot, deposit, register_and_login, set_lot_times
from tests.integration.conftest import new_client


async def sql(statement: str, **params):
    async with AsyncSessionLocal() as session:
        await session.execute(text(statement), params)
        await session.commit()


@pytest.fixture
async def lot_with_bids(client):
    """Live lot with three bids: Ana 100,00 -> Bia 105,00 -> Ana 110,00."""
    await register_and_login(client, "boss@example.com", "AUCTIONEER")
    lot = await create_lot(client, starting_bid="100.00", min_increment="5.00")
    ana, bia = new_client(), new_client()
    for c, email in ((ana, "ana@example.com"), (bia, "bia@example.com")):
        await register_and_login(c, email)
        await deposit(c, "1000.00")
    for c, amount in ((ana, "100.00"), (bia, "105.00"), (ana, "110.00")):
        assert (await bid(c, lot["id"], amount)).status_code == 201
    yield lot, ana
    await ana.aclose()
    await bia.aclose()


async def audit(lot_id):
    public = new_client()  # no login needed
    response = await public.get(f"/audit/lots/{lot_id}")
    await public.aclose()
    assert response.status_code == 200
    return response.json()


def reasons(report) -> set[tuple[str, int | None]]:
    return {(i["reason"], i["seq"]) for i in report["issues"]}


async def test_untouched_history_is_intact(lot_with_bids):
    lot, _ = lot_with_bids

    report = await audit(lot["id"])

    assert report["status"] == "INTACT"
    assert report["issues"] == []
    assert [(b["seq"], b["amount"], b["valid"]) for b in report["bids"]] == [
        (1, "100.00", True),
        (2, "105.00", True),
        (3, "110.00", True),
    ]
    assert all(b["bidder_alias"].startswith("Licitante ") for b in report["bids"])
    assert not {"bidder_id", "email", "name"} & set(report["bids"][0])


async def test_changed_amount(lot_with_bids):
    lot, _ = lot_with_bids
    await sql("UPDATE bids SET amount = 50 WHERE lot_id = :id AND seq = 2", id=lot["id"])

    report = await audit(lot["id"])

    assert report["status"] == "TAMPERED"
    assert reasons(report) == {("HASH_MISMATCH", 2)}
    assert [b["valid"] for b in report["bids"]] == [True, False, True]


@pytest.mark.parametrize(
    "column,value",
    [("created_at", "now()"), ("bidder_id", "(SELECT id FROM users WHERE role = 'AUCTIONEER')")],
)
async def test_changed_time_or_bidder(lot_with_bids, column, value):
    lot, _ = lot_with_bids
    await sql(f"UPDATE bids SET {column} = {value} WHERE lot_id = :id AND seq = 1", id=lot["id"])

    assert reasons(await audit(lot["id"])) == {("HASH_MISMATCH", 1)}


async def test_deleted_bid_in_the_middle(lot_with_bids):
    lot, _ = lot_with_bids
    await sql("DELETE FROM bids WHERE lot_id = :id AND seq = 2", id=lot["id"])

    report = await audit(lot["id"])

    assert ("SEQ_GAP", 3) in reasons(report)
    assert ("PREV_HASH_MISMATCH", 3) in reasons(report)
    assert report["status"] == "TAMPERED"


async def test_deleted_last_bid(lot_with_bids):
    lot, _ = lot_with_bids
    await sql("DELETE FROM bids WHERE lot_id = :id AND seq = 3", id=lot["id"])

    report = await audit(lot["id"])

    assert reasons(report) == {("CHAIN_HEAD_MISMATCH", None), ("LOT_STATE_MISMATCH", None)}


async def test_truncation_with_lot_rewritten_to_match(lot_with_bids):
    lot, _ = lot_with_bids
    await sql(
        """
        WITH prev AS (SELECT bidder_id, amount, hash FROM bids WHERE lot_id = :id AND seq = 2)
        UPDATE lots SET bid_count = 2, current_bid = prev.amount,
               leader_id = prev.bidder_id, chain_head = prev.hash
        FROM prev WHERE lots.id = :id
        """,
        id=lot["id"],
    )
    await sql("DELETE FROM bids WHERE lot_id = :id AND seq = 3", id=lot["id"])

    assert reasons(await audit(lot["id"])) == {("CHAIN_HEAD_MISMATCH", None)}


async def test_inserted_bid(lot_with_bids):
    lot, _ = lot_with_bids
    await sql(
        """
        INSERT INTO bids (lot_id, seq, bidder_id, amount, created_at, prev_hash, hash)
        SELECT lot_id, 4, bidder_id, 999.99, now(), hash, repeat('a', 64)
        FROM bids WHERE lot_id = :id AND seq = 3
        """,
        id=lot["id"],
    )

    report = await audit(lot["id"])

    assert ("HASH_MISMATCH", 4) in reasons(report)
    assert ("CHAIN_HEAD_MISMATCH", None) in reasons(report)


async def test_receipt_and_settled_history(lot_with_bids):
    lot, _ = lot_with_bids
    await set_lot_times(lot["id"], ends_at=datetime.now(UTC) - timedelta(seconds=1))
    await settle_due_lots(AsyncSessionLocal, RecordingNotifier())
    assert (await audit(lot["id"]))["status"] == "INTACT"

    await sql("UPDATE receipts SET amount = 1 WHERE lot_id = :id", id=lot["id"])
    assert reasons(await audit(lot["id"])) == {("RECEIPT_MISMATCH", None)}

    await sql("UPDATE receipts SET amount = 110.00 WHERE lot_id = :id", id=lot["id"])
    await sql("DELETE FROM bids WHERE lot_id = :id AND seq = 3", id=lot["id"])
    report = await audit(lot["id"])
    assert ("RECEIPT_MISMATCH", None) in reasons(report)
    assert ("CHAIN_HEAD_MISMATCH", None) in reasons(report)


async def test_unknown_lot_is_404(client):
    response = await client.get("/audit/lots/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
