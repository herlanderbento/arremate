import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest
from sqlalchemy import select

from account.infra.db.sql_models import UserModel
from auction.application.use_cases.lots.settle_lot import SettleLotInput
from auction.domain.entities.lot import LotId
from auction.infra.composition import build_settle_lot_use_case
from auction.infra.db.sql_models import LotModel, ReceiptModel
from auction.infra.worker.settlement_worker import settle_due_lots
from shared.infra.db.database import AsyncSessionLocal
from tests.fakes.notifier import RecordingNotifier
from tests.helpers import bid, create_lot, deposit, register_and_login, set_lot_times, wallet
from tests.integration.conftest import new_client
from wallet.infra.db.sql_models import WalletModel, WalletTransactionModel


def _past(seconds=1):
    return datetime.now(UTC) - timedelta(seconds=seconds)


@pytest.fixture
async def sold_lot(client):
    """Ana outbids Bia and wins at R$ 105,00; the lot's end is then moved into the past."""
    await register_and_login(client, "boss@example.com", "AUCTIONEER")
    lot = await create_lot(client, starting_bid="100.00", min_increment="5.00")
    ana, bia = new_client(), new_client()
    await register_and_login(ana, "ana@example.com")
    await register_and_login(bia, "bia@example.com")
    await deposit(ana, "500.00")
    await deposit(bia, "500.00")
    await bid(bia, lot["id"], "100.00")
    await bid(ana, lot["id"], "105.00")
    await set_lot_times(lot["id"], ends_at=_past())
    yield lot, ana, bia
    await ana.aclose()
    await bia.aclose()


async def _auctioneer_balance(db_session) -> int:
    query = (
        select(WalletModel.balance)
        .join(UserModel, UserModel.id == WalletModel.user_id)
        .where(UserModel.role == "AUCTIONEER")
    )
    return (await db_session.execute(query)).scalar_one()


async def test_worker_settles_winner_auctioneer_and_issues_receipt(sold_lot, notifier, db_session):
    lot, ana, bia = sold_lot

    assert await settle_due_lots(AsyncSessionLocal, notifier) == 1

    assert await wallet(ana) == {
        "balance": "395.00",
        "committed": "0.00",
        "available": "395.00",
    }
    assert await wallet(bia) == {
        "balance": "500.00",
        "committed": "0.00",
        "available": "500.00",
    }
    assert await _auctioneer_balance(db_session) == D("105.00")

    receipt = (await db_session.execute(select(ReceiptModel))).scalar_one()
    lot_row = (await db_session.execute(select(LotModel))).scalar_one()
    assert receipt.amount == D("105.00")
    assert receipt.chain_head == lot_row.chain_head
    assert len(receipt.public_token) >= 40
    assert lot_row.status == "SETTLED" and lot_row.settled_at is not None

    entries = (await db_session.execute(select(WalletTransactionModel))).scalars().all()
    assert sorted((t.type, t.amount) for t in entries if t.type in ("DEBIT", "CREDIT")) == [
        ("CREDIT", D("105.00")),
        ("DEBIT", D("105.00")),
    ]
    winner_alias = (await ana.get(f"/lots/{lot['id']}")).json()["my_alias"]
    assert notifier.events[-1][1] == {
        "type": "lot_closed",
        "lot_id": lot_row.id,
        "winner_alias": winner_alias,
        "final_amount": D("105.00"),
    }


async def test_settlement_is_idempotent(sold_lot, notifier, db_session):
    lot, ana, _ = sold_lot

    assert await settle_due_lots(AsyncSessionLocal, notifier) == 1
    assert await settle_due_lots(AsyncSessionLocal, notifier) == 0
    async with AsyncSessionLocal() as session:
        again = await build_settle_lot_use_case(session, notifier).execute(
            SettleLotInput(lot_id=LotId(value=lot["id"]))
        )

    assert again is False
    assert (await wallet(ana))["balance"] == "395.00"
    assert len((await db_session.execute(select(ReceiptModel))).scalars().all()) == 1


async def test_concurrent_settlements_debit_once(sold_lot, notifier, db_session):
    lot, ana, _ = sold_lot

    async def settle():
        async with AsyncSessionLocal() as session:
            return await build_settle_lot_use_case(session, notifier).execute(
                SettleLotInput(lot_id=LotId(value=lot["id"]))
            )

    results = await asyncio.gather(*(settle() for _ in range(5)))

    assert sorted(results) == [False] * 4 + [True]
    assert (await wallet(ana))["balance"] == "395.00"
    assert await _auctioneer_balance(db_session) == D("105.00")


async def test_lot_without_bids_closes_without_winner(client, notifier, db_session):
    await register_and_login(client, "boss@example.com", "AUCTIONEER")
    lot = await create_lot(client)
    await set_lot_times(lot["id"], ends_at=_past())

    assert await settle_due_lots(AsyncSessionLocal, notifier) == 1

    assert (await db_session.execute(select(ReceiptModel))).scalars().all() == []
    assert (await db_session.execute(select(LotModel.status))).scalar_one() == "SETTLED"
    assert notifier.events[-1][1]["winner_alias"] is None


async def test_lots_still_running_are_not_settled(client, notifier):
    await register_and_login(client, "boss@example.com", "AUCTIONEER")
    await create_lot(client)

    assert await settle_due_lots(AsyncSessionLocal, notifier) == 0


async def test_viewing_an_overdue_lot_settles_it_first(sold_lot, notifier):
    lot, _, _ = sold_lot
    public = new_client()

    detail = (await public.get(f"/lots/{lot['id']}")).json()
    await public.aclose()

    assert detail["status"] == "ended"
    assert notifier.types()[-1] == "lot_closed"


async def test_auctioneer_panel_shows_result_and_total(sold_lot, client):
    lot, ana, _ = sold_lot
    await settle_due_lots(AsyncSessionLocal, RecordingNotifier())

    body = (await client.get("/lots/mine")).json()

    winner_alias = (await ana.get(f"/lots/{lot['id']}")).json()["my_alias"]
    assert body["data"][0]["result"] == {
        "sold": True,
        "final_amount": "105.00",
        "winner_alias": winner_alias,
    }
    assert body["total_received"] == "105.00"


async def test_total_received_is_not_limited_to_the_current_page(sold_lot, client, catalog):
    lot, _, _ = sold_lot
    await settle_due_lots(AsyncSessionLocal, RecordingNotifier())
    unsold = await create_lot(client, starting_bid="100.00", min_increment="5.00")

    page = (await client.get("/lots/mine", params={"per_page": 1})).json()

    assert [item["id"] for item in page["data"]] == [unsold["id"]]
    assert page["meta"] == {"total": 2, "current_page": 1, "per_page": 1, "last_page": 2}
    assert page["total_received"] == "105.00"
