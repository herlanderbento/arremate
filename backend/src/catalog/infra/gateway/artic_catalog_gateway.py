import logging
import time
from typing import Any

import httpx

from catalog.domain.catalog_gateway import (
    CatalogGateway,
    CatalogSearchInput,
    CatalogSearchOutput,
    ExternalCatalogUnavailable,
)
from catalog.domain.catalog_item import CatalogItem

logger = logging.getLogger(__name__)

FIELDS = "id,title,image_id,artist_title,date_display,medium_display,dimensions"
MAX_SEARCH_LIMIT = 100
IMAGE_URL = "https://www.artic.edu/iiif/2/{image_id}/full/843,/0/default.jpg"
_ATTRIBUTES = {
    "artist": "artist_title",
    "date": "date_display",
    "medium": "medium_display",
    "dimensions": "dimensions",
}


def to_catalog_item(raw: dict[str, Any]) -> CatalogItem | None:
    if not raw.get("image_id") or raw.get("id") is None:
        return None
    return CatalogItem(
        external_id=str(raw["id"]),
        title=(raw.get("title") or "Sem título").strip(),
        image_url=IMAGE_URL.format(image_id=raw["image_id"]),
        attributes={key: str(raw[src]) for key, src in _ATTRIBUTES.items() if raw.get(src)},
    )


class _TtlCache:
    def __init__(self, ttl_seconds: float):
        self.ttl = ttl_seconds
        self._entries: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._entries.get(key)
        if entry is None or time.monotonic() - entry[0] > self.ttl:
            self._entries.pop(key, None)
            return None
        return entry[1]

    def set(self, key: str, value: Any) -> None:
        self._entries[key] = (time.monotonic(), value)


class ArticCatalogGateway(CatalogGateway):
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 5.0,
        cache_ttl_seconds: float = 300,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds
        self._transport = transport
        self._cache = _TtlCache(cache_ttl_seconds)

    async def search_items(self, props: CatalogSearchInput) -> CatalogSearchOutput:
        # The museum ranks by relevance, so props.sort/sort_dir have no equivalent here.
        term = ((props.filter.query if props.filter else None) or "").strip()
        limit = min(props.per_page, MAX_SEARCH_LIMIT)
        key = f"search:{term.lower()}:{props.page}:{limit}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        body = await self._get(
            "/artworks/search",
            {"q": term, "fields": FIELDS, "limit": limit, "page": props.page},
        )
        items = [item for raw in body.get("data") or [] if (item := to_catalog_item(raw))]
        output = CatalogSearchOutput(
            items=items,
            total=(body.get("pagination") or {}).get("total", len(items)),
            current_page=props.page,
            per_page=limit,
        )
        self._cache.set(key, output)
        return output

    async def get_item(self, external_id: str) -> CatalogItem | None:
        if not external_id.isdigit():
            return None
        key = f"item:{external_id}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        body = await self._get(f"/artworks/{external_id}", {"fields": FIELDS}, allow_404=True)
        item = to_catalog_item(body.get("data") or {}) if body else None
        if item is not None:
            self._cache.set(key, item)
        return item

    async def _get(
        self, path: str, params: dict[str, Any], allow_404: bool = False
    ) -> dict[str, Any] | None:
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                transport=self._transport,
                headers={"AIC-User-Agent": "arremate-api"},
            ) as client:
                response = await client.get(path, params=params)
        except httpx.HTTPError as exc:
            logger.warning("Catalog request failed: %s %s", path, exc)
            raise ExternalCatalogUnavailable() from exc

        if allow_404 and response.status_code == 404:
            return None
        if response.status_code >= 400:
            logger.warning("Catalog answered %s for %s", response.status_code, path)
            raise ExternalCatalogUnavailable()
        try:
            return response.json()
        except ValueError as exc:
            raise ExternalCatalogUnavailable() from exc
