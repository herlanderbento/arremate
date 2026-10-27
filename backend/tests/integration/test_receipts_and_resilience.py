from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from auction.infra.db.sql_models import ReceiptModel
from auction.infra.worker.settlement_worker import settle_due_lots
from shared.infra.db.database import AsyncSessionLocal
from tests.fakes.notifier import RecordingNotifier
from tests.helpers import bid, create_lot, deposit, register_and_login, set_lot_times
from tests.integration.conftest import new_client


@pytest.fixture
async def won_lot(client, db_session):
    await register_and_login(client, "boss@example.com", "AUCTIONEER")
    lot = await create_lot(client, starting_bid="100.00")
    ana = new_client()
    await register_and_login(ana, "ana@example.com")
    await deposit(ana, "500.00")
    await bid(ana, lot["id"], "120.00")
    await set_lot_times(lot["id"], ends_at=datetime.now(UTC) - timedelta(seconds=1))
    await settle_due_lots(AsyncSessionLocal, RecordingNotifier())
    token = (await db_session.execute(select(ReceiptModel.public_token))).scalar_one()
    yield lot, ana, token
    await ana.aclose()


async def test_receipt_is_public_and_has_no_personal_data(won_lot):
    lot, ana, token = won_lot
    public = new_client()

    response = await public.get(f"/receipts/{token}")
    await public.aclose()

    assert response.status_code == 200
    body = response.json()
    my_alias = (await ana.get(f"/lots/{lot['id']}")).json()["my_alias"]
    assert body["winner_alias"] == my_alias
    assert (body["amount"], body["bid_count"], body["title"]) == ("120.00", 1, "Water Lilies")
    assert body["audit_url"] == f"/audit/lots/{lot['id']}"
    assert len(body["chain_head"]) == 64
    assert "ana@example.com" not in response.text and "Ana" not in response.text


async def test_unknown_receipt_is_404(client):
    assert (await client.get("/receipts/does-not-exist-123")).status_code == 404


async def test_everything_public_works_with_the_catalog_down(won_lot, catalog):
    """Only searching the catalog and creating lots depend on the external API."""
    lot, _, token = won_lot
    catalog.down = True
    public = new_client()

    responses = [
        await public.get("/lots"),
        await public.get(f"/lots/{lot['id']}"),
        await public.get(f"/audit/lots/{lot['id']}"),
        await public.get(f"/receipts/{token}"),
    ]
    await public.aclose()

    assert [r.status_code for r in responses] == [200, 200, 200, 200]
    assert catalog.calls == 1  # only the lot creation in the fixture
