from catalog.domain.catalog_gateway import (
    CatalogGateway,
    CatalogSearchInput,
    CatalogSearchOutput,
    ExternalCatalogUnavailable,
)
from catalog.domain.catalog_item import CatalogItem

MONET = CatalogItem(
    external_id="16568",
    title="Water Lilies",
    image_url="https://www.artic.edu/iiif/2/abc/full/843,/0/default.jpg",
    attributes={"artist": "Claude Monet", "date": "1906"},
)


class FakeCatalogGateway(CatalogGateway):
    def __init__(self, items: list[CatalogItem] | None = None):
        self.items = {i.external_id: i for i in (items if items is not None else [MONET])}
        self.down = False
        self.calls = 0

    async def search_items(self, props: CatalogSearchInput) -> CatalogSearchOutput:
        self._call()
        term = ((props.filter.query if props.filter else None) or "").strip().lower()
        found = [i for i in self.items.values() if term in i.title.lower()]
        start = (props.page - 1) * props.per_page
        return CatalogSearchOutput(
            items=found[start : start + props.per_page],
            total=len(found),
            current_page=props.page,
            per_page=props.per_page,
        )

    async def get_item(self, external_id: str) -> CatalogItem | None:
        self._call()
        return self.items.get(external_id)

    def _call(self) -> None:
        self.calls += 1
        if self.down:
            raise ExternalCatalogUnavailable()
