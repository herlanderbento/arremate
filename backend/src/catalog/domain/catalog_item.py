from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CatalogItem:
    external_id: str
    title: str
    image_url: str
    attributes: dict[str, str] = field(default_factory=dict)
