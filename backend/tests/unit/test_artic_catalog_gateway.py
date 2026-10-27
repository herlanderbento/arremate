import httpx
import pytest

from catalog.domain.catalog_gateway import (
    CatalogFilter,
    CatalogSearchInput,
    ExternalCatalogUnavailable,
)
from catalog.infra.gateway.artic_catalog_gateway import ArticCatalogGateway

SEARCH_BODY = {
    "data": [
        {
            "id": 16568,
            "title": "Water Lilies",
            "image_id": "3c27b499-af56-f0d5-93b5-a7f2f1ad5813",
            "artist_title": "Claude Monet",
            "date_display": "1906",
            "medium_display": "Oil on canvas",
            "dimensions": "89.9 × 94.1 cm",
        },
        {"id": 1, "title": "No image", "image_id": None},
    ],
    "pagination": {"total": 37},
}


def _props(term: str, page: int = 1, per_page: int = 12) -> CatalogSearchInput:
    return CatalogSearchInput(
        init_page=page,
        init_per_page=per_page,
        init_filter=CatalogFilter(query=term),
    )


def _gateway(handler, **kwargs) -> tuple[ArticCatalogGateway, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def recording(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    gateway = ArticCatalogGateway(
        "https://api.example/api/v1", transport=httpx.MockTransport(recording), **kwargs
    )
    return gateway, requests


async def test_search_maps_items_and_drops_those_without_image():
    gateway, requests = _gateway(lambda r: httpx.Response(200, json=SEARCH_BODY))

    output = await gateway.search_items(_props("monet"))

    assert len(output.items) == 1
    item = output.items[0]
    assert item.external_id == "16568"
    assert item.title == "Water Lilies"
    assert item.image_url == (
        "https://www.artic.edu/iiif/2/3c27b499-af56-f0d5-93b5-a7f2f1ad5813/full/843,/0/default.jpg"
    )
    assert item.attributes == {
        "artist": "Claude Monet",
        "date": "1906",
        "medium": "Oil on canvas",
        "dimensions": "89.9 × 94.1 cm",
    }
    params = requests[0].url.params
    assert requests[0].url.path == "/api/v1/artworks/search"
    assert (params["q"], params["limit"], params["page"]) == ("monet", "12", "1")
    assert "image_id" in params["fields"]


async def test_pagination_comes_from_the_museum_total():
    gateway, requests = _gateway(lambda r: httpx.Response(200, json=SEARCH_BODY))

    output = await gateway.search_items(_props("monet", page=3, per_page=10))

    assert (output.total, output.current_page, output.per_page) == (37, 3, 10)
    assert output.last_page == 4
    assert (requests[0].url.params["page"], requests[0].url.params["limit"]) == ("3", "10")


async def test_per_page_is_capped():
    gateway, requests = _gateway(lambda r: httpx.Response(200, json=SEARCH_BODY))

    output = await gateway.search_items(_props("monet", per_page=5000))

    assert requests[0].url.params["limit"] == "100"
    assert output.per_page == 100


async def test_total_falls_back_to_item_count_without_pagination_block():
    body = {"data": SEARCH_BODY["data"]}
    gateway, _ = _gateway(lambda r: httpx.Response(200, json=body))

    output = await gateway.search_items(_props("monet"))

    assert output.total == 1


async def test_search_is_cached_per_query():
    gateway, requests = _gateway(lambda r: httpx.Response(200, json=SEARCH_BODY))

    await gateway.search_items(_props("monet"))
    await gateway.search_items(_props(" Monet "))
    await gateway.search_items(_props("degas"))

    assert len(requests) == 2


async def test_cache_is_per_page():
    gateway, requests = _gateway(lambda r: httpx.Response(200, json=SEARCH_BODY))

    await gateway.search_items(_props("monet", page=1))
    await gateway.search_items(_props("monet", page=2))
    await gateway.search_items(_props("monet", page=1))

    assert len(requests) == 2


async def test_cache_expires():
    gateway, requests = _gateway(
        lambda r: httpx.Response(200, json=SEARCH_BODY), cache_ttl_seconds=0
    )

    await gateway.search_items(_props("monet"))
    await gateway.search_items(_props("monet"))

    assert len(requests) == 2


@pytest.mark.parametrize(
    "handler",
    [
        lambda r: httpx.Response(500),
        lambda r: httpx.Response(429),
        lambda r: httpx.Response(200, text="<html>not json</html>"),
        lambda r: (_ for _ in ()).throw(httpx.ConnectTimeout("timeout", request=r)),
        lambda r: (_ for _ in ()).throw(httpx.ConnectError("dns", request=r)),
    ],
    ids=["5xx", "rate-limited", "not-json", "timeout", "network"],
)
async def test_failures_become_catalog_unavailable(handler):
    gateway, _ = _gateway(handler)

    with pytest.raises(ExternalCatalogUnavailable) as exc:
        await gateway.search_items(_props("monet"))
    assert exc.value.code == "CATALOG_UNAVAILABLE"


async def test_failures_are_not_cached():
    responses = iter([httpx.Response(500), httpx.Response(200, json=SEARCH_BODY)])
    gateway, _ = _gateway(lambda r: next(responses))

    with pytest.raises(ExternalCatalogUnavailable):
        await gateway.search_items(_props("monet"))
    assert len((await gateway.search_items(_props("monet"))).items) == 1


async def test_get_item():
    gateway, requests = _gateway(
        lambda r: httpx.Response(200, json={"data": SEARCH_BODY["data"][0]})
    )

    item = await gateway.get_item("16568")

    assert item is not None and item.title == "Water Lilies"
    assert requests[0].url.path == "/api/v1/artworks/16568"


async def test_get_item_missing_or_without_image_is_none():
    not_found, _ = _gateway(lambda r: httpx.Response(404, json={"status": 404}))
    no_image, _ = _gateway(lambda r: httpx.Response(200, json={"data": SEARCH_BODY["data"][1]}))
    bad_id, requests = _gateway(lambda r: httpx.Response(200, json={}))

    assert await not_found.get_item("999") is None
    assert await no_image.get_item("1") is None
    assert await bad_id.get_item("../users") is None
    assert requests == []
