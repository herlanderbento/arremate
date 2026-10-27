from tests.helpers import register_and_login


async def test_auctioneer_searches_catalog(client, catalog):
    await register_and_login(client, "boss@example.com", "AUCTIONEER")

    response = await client.get("/catalog/search", params={"filter": "lilies"})

    assert response.status_code == 200
    assert response.json() == {
        "data": [
            {
                "external_id": "16568",
                "title": "Water Lilies",
                "image_url": "https://www.artic.edu/iiif/2/abc/full/843,/0/default.jpg",
                "attributes": {"artist": "Claude Monet", "date": "1906"},
            }
        ],
        "meta": {"total": 1, "current_page": 1, "per_page": 12, "last_page": 1},
    }


async def test_catalog_search_is_paginated(client, catalog):
    await register_and_login(client, "boss@example.com", "AUCTIONEER")

    response = await client.get(
        "/catalog/search", params={"filter": "lilies", "page": 2, "per_page": 1}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"] == []
    assert body["meta"] == {"total": 1, "current_page": 2, "per_page": 1, "last_page": 1}


async def test_catalog_search_is_auctioneer_only(client, catalog):
    assert (await client.get("/catalog/search", params={"filter": "x1"})).status_code == 401

    await register_and_login(client, "ana@example.com", "BIDDER")
    assert (await client.get("/catalog/search", params={"filter": "x1"})).status_code == 403
    assert catalog.calls == 0


async def test_catalog_down_is_503_with_code(client, catalog):
    await register_and_login(client, "boss@example.com", "AUCTIONEER")
    catalog.down = True

    response = await client.get("/catalog/search", params={"filter": "lilies"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "CATALOG_UNAVAILABLE"


async def test_query_is_validated(client, catalog):
    await register_and_login(client, "boss@example.com", "AUCTIONEER")

    assert (await client.get("/catalog/search", params={"filter": "a"})).status_code == 422
    assert (await client.get("/catalog/search")).status_code == 422
    assert (await client.get("/catalog/search", params={"q": "lilies"})).status_code == 422
