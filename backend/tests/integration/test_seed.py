from decimal import Decimal as D

from sqlalchemy import func, select, update

from auction.infra.db.sql_models import BidModel, LotModel, ReceiptModel
from scripts.seed import BIDDERS, PASSWORD, seed
from shared.infra.db.database import AsyncSessionLocal
from tests.integration.conftest import new_client


async def test_seed_creates_a_walkable_demo_and_is_idempotent(client, db_session):
    assert await seed() == "Seed applied."
    assert await seed() == "Seed already applied; nothing to do."

    lots = (await client.get("/lots")).json()["data"]
    statuses = sorted(lot["status"] for lot in lots)
    assert statuses == ["ended", "live", "live", "scheduled"]
    live_with_bids = [lot for lot in lots if lot["status"] == "live" and lot["bid_count"] > 0]
    assert len(live_with_bids) == 1 and live_with_bids[0]["bid_count"] == 3
    assert len((await db_session.execute(select(ReceiptModel))).scalars().all()) == 1

    for lot in lots:
        assert (await client.get(f"/audit/lots/{lot['id']}")).json()["status"] == "INTACT"

    # Both seeded bidders can log in and see their wallets (balance minus what they hold).
    for _, email in BIDDERS:
        bidder = new_client()
        login = await bidder.post("/auth/login", json={"email": email, "password": PASSWORD})
        assert login.status_code == 200
        wallet = (await bidder.get("/wallet")).json()
        assert D(wallet["available"]) == D(wallet["balance"]) - D(wallet["committed"])
        await bidder.aclose()


async def test_refresh_live_creates_a_new_live_lot_only_when_needed(client):
    await seed()
    assert await seed(refresh_live=True) == "A live lot with bids already exists; nothing to do."

    # Simulate the evaluator arriving after the seeded live lot ended.
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(LotModel)
            .where(LotModel.bid_count > 0, LotModel.status == "ACTIVE")
            .values(starts_at=func.now() - func.make_interval(0, 0, 0, 2), ends_at=func.now())
        )
        await session.commit()

    assert await seed(refresh_live=True) == "Created a new live lot with bids."
    async with AsyncSessionLocal() as session:
        bids = (await session.execute(select(func.count(BidModel.id)))).scalar_one()
    assert bids == 3 + 2 + 3
