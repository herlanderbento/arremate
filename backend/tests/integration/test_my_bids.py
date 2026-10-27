from datetime import UTC, datetime, timedelta

from auction.infra.worker.settlement_worker import settle_due_lots
from catalog.domain.catalog_item import CatalogItem
from shared.infra.db.database import AsyncSessionLocal
from tests.fakes.notifier import RecordingNotifier
from tests.helpers import bid, create_lot, deposit, register_and_login, set_lot_times
from tests.integration.conftest import new_client


async def test_my_bids_shows_each_situation(client):
    await register_and_login(client, "boss@example.com", "AUCTIONEER")
    winning, outbid, won, lost = [await create_lot(client) for _ in range(4)]
    untouched = await create_lot(client)
    ana, bia = new_client(), new_client()
    for c, email in ((ana, "ana@example.com"), (bia, "bia@example.com")):
        await register_and_login(c, email)
        await deposit(c, "10000.00")

    await bid(ana, winning["id"], "100.00")
    await bid(ana, outbid["id"], "100.00")
    await bid(bia, outbid["id"], "120.00")
    await bid(ana, won["id"], "100.00")
    await bid(bia, won["id"], "105.00")
    await bid(ana, won["id"], "200.00")
    await bid(ana, lost["id"], "100.00")
    await bid(bia, lost["id"], "150.00")
    for lot in (won, lost):
        await set_lot_times(lot["id"], ends_at=datetime.now(UTC) - timedelta(seconds=1))
    await settle_due_lots(AsyncSessionLocal, RecordingNotifier())

    body = (await ana.get("/me/bids")).json()
    await ana.aclose()
    await bia.aclose()

    by_lot = {item["id"]: item for item in body["data"]}
    assert body["meta"] == {"total": 4, "current_page": 1, "per_page": 12, "last_page": 1}
    assert untouched["id"] not in by_lot
    assert {lot_id: item["situation"] for lot_id, item in by_lot.items()} == {
        winning["id"]: "winning",
        outbid["id"]: "outbid",
        won["id"]: "won",
        lost["id"]: "lost",
    }
    assert by_lot[won["id"]]["my_max_bid"] == "200.00"
    assert by_lot[outbid["id"]]["my_max_bid"] == "100.00"
    assert by_lot[won["id"]]["receipt_token"]
    assert all(
        by_lot[i]["receipt_token"] is None for i in (winning["id"], outbid["id"], lost["id"])
    )
    receipt = await client.get(f"/receipts/{by_lot[won['id']]['receipt_token']}")
    assert receipt.json()["winner_alias"] == by_lot[won["id"]]["my_alias"]


async def test_my_bids_filters_by_title_and_paginates(client, catalog):
    catalog.items["99"] = CatalogItem(
        external_id="99",
        title="Nighthawks",
        image_url="https://www.artic.edu/iiif/2/x/full/843,/0/default.jpg",
    )
    await register_and_login(client, "boss@example.com", "AUCTIONEER")
    lilies = await create_lot(client)
    night = await create_lot(client, external_id="99")
    other = await create_lot(client)
    ana = new_client()
    await register_and_login(ana, "ana@example.com")
    await deposit(ana, "10000.00")
    await bid(ana, lilies["id"], "100.00")
    await bid(ana, night["id"], "100.00")
    await bid(ana, other["id"], "100.00")

    filtered = (await ana.get("/me/bids", params={"filter": "night"})).json()
    wildcard = (await ana.get("/me/bids", params={"filter": "%"})).json()
    page1 = (await ana.get("/me/bids", params={"per_page": 2})).json()
    page2 = (await ana.get("/me/bids", params={"page": 2, "per_page": 2})).json()
    await ana.aclose()

    assert [item["title"] for item in filtered["data"]] == ["Nighthawks"]
    assert filtered["meta"]["total"] == 1
    assert wildcard["meta"]["total"] == 0
    assert page1["meta"]["total"] == 3 and len(page1["data"]) == 2
    assert len(page2["data"]) == 1
    assert (page2["meta"]["current_page"], page2["meta"]["last_page"]) == (2, 2)
    ids = {item["id"] for item in page1["data"]} | {item["id"] for item in page2["data"]}
    assert ids == {lilies["id"], night["id"], other["id"]}


async def test_my_bids_is_bidder_only(client):
    assert (await client.get("/me/bids")).status_code == 401
    await register_and_login(client, "boss@example.com", "AUCTIONEER")
    assert (await client.get("/me/bids")).status_code == 403
