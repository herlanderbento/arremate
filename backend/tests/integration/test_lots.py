from datetime import UTC, datetime, timedelta

from tests.fakes.catalog import CatalogItem
from tests.helpers import at, create_lot, register_and_login, set_lot_times
from tests.integration.conftest import new_client


async def _auctioneer(client, email="boss@example.com"):
    return await register_and_login(client, email, "AUCTIONEER")


async def test_create_lot_snapshots_catalog_item(client, catalog):
    await _auctioneer(client)

    lot = await create_lot(client, starting_bid="100.00", min_increment="5.00")

    assert lot["title"] == "Water Lilies"
    assert lot["image_url"].startswith("https://www.artic.edu/iiif/")
    assert lot["attributes"] == {"artist": "Claude Monet", "date": "1906"}
    assert lot["status"] == "live"
    assert (lot["current_bid"], lot["min_next_bid"], lot["bid_count"]) == (
        None,
        "100.00",
        0,
    )


async def test_client_cannot_override_catalog_data(client):
    await _auctioneer(client)

    response = await client.post(
        "/lots",
        json={
            "external_id": "16568",
            "title": "Fake title",
            "image_url": "https://evil.example/x.jpg",
            "starting_bid": "1.00",
            "min_increment": "1.00",
            "starts_at": at(minutes=-1),
            "ends_at": at(hours=1),
        },
    )

    assert response.json()["title"] == "Water Lilies"
    assert "evil" not in response.json()["image_url"]


async def test_create_lot_refusals(client, catalog):
    await _auctioneer(client)

    async def post(**overrides):
        body = {
            "external_id": "16568",
            "starting_bid": "10.00",
            "min_increment": "1.00",
            "starts_at": at(minutes=-1),
            "ends_at": at(hours=1),
            **overrides,
        }
        response = await client.post("/lots", json=body)
        return response.status_code, response.json()["error"]["code"]

    assert await post(external_id="404") == (422, "CATALOG_ITEM_NOT_FOUND")
    assert await post(starting_bid="0.00") == (422, "INVALID_AMOUNT")
    assert await post(starts_at=at(hours=2)) == (422, "INVALID_SCHEDULE")
    assert await post(ends_at=at(minutes=-1)) == (422, "INVALID_SCHEDULE")
    assert await post(ends_at="2026-12-01T10:00:00") == (422, "VALIDATION_ERROR")  # no timezone
    catalog.down = True
    assert await post() == (503, "CATALOG_UNAVAILABLE")


async def test_only_auctioneers_create_lots(client):
    await register_and_login(client, "ana@example.com", "BIDDER")

    response = await client.post("/lots", json={})

    assert response.status_code == 403


async def _showcase_fixture(client, catalog):
    catalog.items["2"] = CatalogItem("2", "Nighthawks", "https://img/2", {})
    catalog.items["3"] = CatalogItem("3", "American Gothic", "https://img/3", {})
    catalog.items["4"] = CatalogItem("4", "The Bedroom", "https://img/4", {})
    await _auctioneer(client)
    live_late = await create_lot(client, "16568", ends_at=at(hours=3))
    live_soon = await create_lot(client, "2", ends_at=at(hours=1))
    scheduled = await create_lot(client, "3", starts_at=at(hours=1), ends_at=at(hours=2))
    ended = await create_lot(client, "4")
    await set_lot_times(ended["id"], ends_at=datetime.now(UTC) - timedelta(minutes=5))
    cancelled = await create_lot(client, "16568")
    assert (await client.post(f"/lots/{cancelled['id']}/cancel")).status_code == 200
    return live_late, live_soon, scheduled, ended, cancelled


async def test_showcase_groups_and_orders_and_hides_cancelled(client, catalog):
    live_late, live_soon, scheduled, ended, cancelled = await _showcase_fixture(client, catalog)
    public = new_client()

    everything = (await public.get("/lots")).json()
    live = (await public.get("/lots", params={"status": "live"})).json()
    upcoming = (await public.get("/lots", params={"status": "scheduled"})).json()
    finished = (await public.get("/lots", params={"status": "ended"})).json()
    await public.aclose()

    ids = [lot["id"] for lot in everything["data"]]
    assert ids == [live_soon["id"], live_late["id"], scheduled["id"], ended["id"]]
    assert cancelled["id"] not in ids
    assert everything["meta"] == {
        "total": 4,
        "current_page": 1,
        "per_page": 12,
        "last_page": 1,
    }
    assert [lot["id"] for lot in live["data"]] == [live_soon["id"], live_late["id"]]
    assert [lot["status"] for lot in upcoming["data"]] == ["scheduled"]
    assert [lot["status"] for lot in finished["data"]] == ["ended"]


async def test_showcase_search_and_pagination(client, catalog):
    await _showcase_fixture(client, catalog)

    search = (await client.get("/lots", params={"filter": "night"})).json()
    wildcard = (await client.get("/lots", params={"filter": "%"})).json()
    page2 = (await client.get("/lots", params={"page": 2, "per_page": 3})).json()

    assert [lot["title"] for lot in search["data"]] == ["Nighthawks"]
    assert wildcard["meta"]["total"] == 0  # '%' is matched literally
    assert len(page2["data"]) == 1 and page2["meta"]["total"] == 4
    assert (page2["meta"]["current_page"], page2["meta"]["last_page"]) == (2, 2)
    assert (await client.get("/lots", params={"status": "cancelled"})).status_code == 422


async def test_lot_detail_is_public(client):
    await _auctioneer(client)
    lot = await create_lot(client)
    public = new_client()

    response = await public.get(f"/lots/{lot['id']}")
    await public.aclose()

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == lot["id"]
    assert (body["bids"], body["leader_alias"], body["my_alias"]) == ([], None, None)
    server_time = datetime.fromisoformat(body["server_time"])
    assert abs((server_time - datetime.now(UTC)).total_seconds()) < 5


async def test_lot_detail_includes_my_alias_for_bidders_only(client):
    await _auctioneer(client)
    lot = await create_lot(client)
    bidder = new_client()
    await register_and_login(bidder, "ana@example.com", "BIDDER")

    as_bidder = (await bidder.get(f"/lots/{lot['id']}")).json()
    as_owner = (await client.get(f"/lots/{lot['id']}")).json()
    await bidder.aclose()

    assert as_bidder["my_alias"].startswith("Licitante ")
    assert as_owner["my_alias"] is None


async def test_unknown_or_cancelled_lot_is_404(client):
    await _auctioneer(client)
    lot = await create_lot(client)
    await client.post(f"/lots/{lot['id']}/cancel")

    assert (await client.get(f"/lots/{lot['id']}")).status_code == 404
    assert (await client.get("/lots/00000000-0000-0000-0000-000000000000")).status_code == 404
    assert (await client.get("/lots/not-a-uuid")).status_code == 422


async def test_only_the_owner_cancels(client):
    await _auctioneer(client)
    lot = await create_lot(client)
    other = new_client()
    await _auctioneer(other, "other@example.com")

    response = await other.post(f"/lots/{lot['id']}/cancel")
    await other.aclose()

    assert (response.status_code, response.json()["error"]["code"]) == (403, "NOT_OWNER")


async def test_cannot_cancel_an_ended_lot(client):
    await _auctioneer(client)
    lot = await create_lot(client)
    await set_lot_times(lot["id"], ends_at=datetime.now(UTC) - timedelta(seconds=1))

    response = await client.post(f"/lots/{lot['id']}/cancel")

    assert (response.status_code, response.json()["error"]["code"]) == (422, "LOT_NOT_CANCELLABLE")


async def test_my_lots_lists_own_lots_including_cancelled(client):
    await _auctioneer(client)
    kept = await create_lot(client)
    cancelled = await create_lot(client)
    await client.post(f"/lots/{cancelled['id']}/cancel")
    other = new_client()
    await _auctioneer(other, "other@example.com")
    await create_lot(other)
    await other.aclose()

    body = (await client.get("/lots/mine")).json()

    assert {(lot["id"], lot["status"]) for lot in body["data"]} == {
        (kept["id"], "live"),
        (cancelled["id"], "cancelled"),
    }
    assert body["data"][0]["result"] == {
        "sold": False,
        "final_amount": None,
        "winner_alias": None,
    }
    assert body["total_received"] == "0.00"
    assert body["meta"] == {"total": 2, "current_page": 1, "per_page": 12, "last_page": 1}


async def test_my_lots_paginates_without_shrinking_the_total_received(client):
    await _auctioneer(client)
    await create_lot(client)
    await create_lot(client)

    page1 = (await client.get("/lots/mine", params={"per_page": 1})).json()
    page2 = (await client.get("/lots/mine", params={"per_page": 1, "page": 2})).json()

    assert (len(page1["data"]), len(page2["data"])) == (1, 1)
    assert page1["data"][0]["id"] != page2["data"][0]["id"]
    assert page1["meta"] == {"total": 2, "current_page": 1, "per_page": 1, "last_page": 2}
    assert page1["total_received"] == page2["total_received"] == "0.00"


async def test_my_lots_is_auctioneer_only(client):
    await register_and_login(client, "ana@example.com", "BIDDER")

    assert (await client.get("/lots/mine")).status_code == 403


async def test_cancel_with_bids_refunds_the_leader(client, notifier):
    await _auctioneer(client)
    lot = await create_lot(client)
    ana, bia = new_client(), new_client()
    for c, email in ((ana, "ana@example.com"), (bia, "bia@example.com")):
        await register_and_login(c, email)
        await c.post("/wallet/deposit", json={"amount": "500.00"})
    await ana.post(f"/lots/{lot['id']}/bids", json={"amount": "100.00"})
    await bia.post(f"/lots/{lot['id']}/bids", json={"amount": "120.00"})

    response = await client.post(f"/lots/{lot['id']}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    for c in (ana, bia):
        assert (await c.get("/wallet")).json() == {
            "balance": "500.00",
            "committed": "0.00",
            "available": "500.00",
        }
    late = await bia.post(f"/lots/{lot['id']}/bids", json={"amount": "200.00"})
    assert late.json()["error"]["code"] == "LOT_ENDED"
    assert notifier.types()[-1] == "lot_cancelled"
    await ana.aclose()
    await bia.aclose()
