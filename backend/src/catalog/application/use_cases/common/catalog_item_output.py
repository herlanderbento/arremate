from dataclasses import dataclass

from catalog.domain.catalog_item import CatalogItem


@dataclass(frozen=True, slots=True)
class CatalogItemOutput:
    external_id: str
    title: str
    image_url: str
    attributes: dict[str, str]

    @classmethod
    def from_entity(cls, item: CatalogItem) -> "CatalogItemOutput":
        return cls(
            external_id=item.external_id,
            title=item.title,
            image_url=item.image_url,
            attributes=item.attributes,
        )
