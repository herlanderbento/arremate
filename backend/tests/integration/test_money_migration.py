import asyncio
import hashlib
import hmac
import os
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from pathlib import Path

import asyncpg
from alembic import command
from alembic.config import Config

from tests.conftest import TEST_DATABASE_URL
from tests.integration.conftest import new_client

ROOT = Path(__file__).resolve().parents[2]
DSN = TEST_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
KEY = os.environ["AUDIT_SECRET"].encode()


def _alembic() -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    return config


def h(message: str) -> str:
    return hmac.new(KEY, message.encode(), hashlib.sha256).hexdigest()


def ts(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def old_chain(lot_id, bids):
    """The pre-0003 sealing: amount as integer cents."""
    prev, rows = h(f"genesis|{lot_id}"), []
    for seq, (bidder, cents, created_at) in enumerate(bids, start=1):
        bid_hash = h(f"{prev}|{lot_id}|{seq}|{bidder}|{cents}|{ts(created_at)}")
        rows.append((uuid.uuid4(), seq, bidder, cents, created_at, prev, bid_hash))
        prev = bid_hash
    return rows, h(f"head|{lot_id}|{len(bids)}|{prev}")


async def _insert_old_format() -> dict:
    conn = await asyncpg.connect(DSN)
    try:
        boss, ana, bia = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        for user_id, role, cents in (
            (boss, "AUCTIONEER", 10500),
            (ana, "BIDDER", 100000),
            (bia, "BIDDER", 39500),
        ):
            await conn.execute(
                "INSERT INTO users (id, role, name, email, password_hash) "
                "VALUES ($1, $2, 'x', $3, 'x')",
                user_id,
                role,
                f"{user_id}@example.com",
            )
            await conn.execute(
                "INSERT INTO wallets (user_id, balance_cents, committed_cents) VALUES ($1, $2, $3)",
                user_id,
                cents,
                20000 if user_id == ana else 0,
            )

        now = datetime.now(UTC).replace(microsecond=123456)
        lots = {}
        # Intact and settled: Ana 100,00 -> Bia 105,00 (winner, with receipt).
        # Tampered: Ana 200,00, then someone changes the amount directly in the database.
        for name, bids, status in (
            (
                "intact",
                [
                    (ana, 10000, now - timedelta(minutes=2)),
                    (bia, 10500, now - timedelta(minutes=1)),
                ],
                "SETTLED",
            ),
            ("tampered", [(ana, 20000, now - timedelta(minutes=1))], "ACTIVE"),
        ):
            lot_id = uuid.uuid4()
            rows, head = old_chain(lot_id, bids)
            last = rows[-1]
            await conn.execute(
                """INSERT INTO lots (id, auctioneer_id, external_id, title, starting_bid_cents,
                       min_increment_cents, starts_at, ends_at, status, current_bid_cents,
                       leader_id, bid_count, chain_head)
                   VALUES ($1, $2, '1', $3, 10000, 500, $4, $5, $6, $7, $8, $9, $10)""",
                lot_id,
                boss,
                name,
                now - timedelta(hours=2),
                now + timedelta(hours=1),
                status,
                last[3],
                last[2],
                len(rows),
                head,
            )
            for row in rows:
                await conn.execute(
                    "INSERT INTO bids (id, lot_id, seq, bidder_id, amount_cents, created_at, "
                    "prev_hash, hash) "
                    "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
                    row[0],
                    lot_id,
                    *row[1:],
                )
            lots[name] = {"id": lot_id, "rows": rows, "head": head}

        intact = lots["intact"]
        await conn.execute(
            "INSERT INTO receipts (lot_id, winner_id, winning_bid_id, amount_cents, chain_head, "
            "public_token) "
            "VALUES ($1, $2, $3, 10500, $4, 'token-from-before-0003')",
            intact["id"],
            bia,
            intact["rows"][-1][0],
            intact["head"],
        )
        await conn.execute(
            "UPDATE bids SET amount_cents = 1 WHERE lot_id = $1", lots["tampered"]["id"]
        )
        await conn.execute(
            "UPDATE lots SET current_bid_cents = 1 WHERE id = $1", lots["tampered"]["id"]
        )
        return lots
    finally:
        await conn.close()


async def _read(query: str, *args):
    conn = await asyncpg.connect(DSN)
    try:
        return await conn.fetch(query, *args)
    finally:
        await conn.close()


async def _audit(lot_id) -> dict:
    async with new_client() as client:
        return (await client.get(f"/audit/lots/{lot_id}")).json()


def test_0003_converts_exactly_and_reseals_only_intact_chains():
    config = _alembic()
    command.downgrade(config, "0002")
    try:
        lots = asyncio.run(_insert_old_format())
        command.upgrade(config, "head")

        # Exact conversion: cents / 100, stored as NUMERIC(14,2).
        lot_rows = asyncio.run(
            _read("SELECT title, starting_bid, min_increment, current_bid FROM lots ORDER BY title")
        )
        assert [tuple(r) for r in lot_rows] == [
            ("intact", D("100.00"), D("5.00"), D("105.00")),
            ("tampered", D("100.00"), D("5.00"), D("0.01")),
        ]
        balances = asyncio.run(_read("SELECT balance, committed FROM wallets ORDER BY balance"))
        assert [tuple(r) for r in balances] == [
            (D("105.00"), D("0.00")),
            (D("395.00"), D("0.00")),
            (D("1000.00"), D("200.00")),
        ]
        amounts = asyncio.run(_read("SELECT amount FROM bids ORDER BY amount"))
        assert [r["amount"] for r in amounts] == [D("0.01"), D("100.00"), D("105.00")]

        # Intact history re-sealed: audit and receipt still work.
        intact = asyncio.run(_audit(lots["intact"]["id"]))
        assert intact["status"] == "INTACT"
        assert [b["amount"] for b in intact["bids"]] == ["100.00", "105.00"]

        async def receipt():
            async with new_client() as client:
                return (await client.get("/receipts/token-from-before-0003")).json()

        assert asyncio.run(receipt())["amount"] == "105.00"

        # Tampered before the migration: still tampered.
        tampered = asyncio.run(_audit(lots["tampered"]["id"]))
        assert tampered["status"] == "TAMPERED"
        assert {(i["reason"], i["seq"]) for i in tampered["issues"]} == {("HASH_MISMATCH", 1)}

        # Downgrade restores the original cents and exactly the original hashes.
        command.downgrade(config, "0002")
        restored = asyncio.run(
            _read(
                "SELECT amount_cents, prev_hash, hash FROM bids WHERE lot_id = $1 ORDER BY seq",
                lots["intact"]["id"],
            )
        )
        assert [(r["amount_cents"], r["prev_hash"], r["hash"]) for r in restored] == [
            (row[3], row[5], row[6]) for row in lots["intact"]["rows"]
        ]
        head = asyncio.run(_read("SELECT chain_head FROM lots WHERE id = $1", lots["intact"]["id"]))
        assert head[0]["chain_head"] == lots["intact"]["head"]
    finally:
        command.upgrade(config, "head")
