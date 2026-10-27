from abc import ABC, abstractmethod
from dataclasses import dataclass

from catalog.domain.catalog_item import CatalogItem
from shared.domain.exceptions import GatewayException
from shared.domain.search_input import SearchInput
from shared.domain.search_output import SearchOutput


class ExternalCatalogUnavailable(GatewayException):
    code = "CATALOG_UNAVAILABLE"

    def __init__(self, message: str = "O catálogo de obras está indisponível no momento."):
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class CatalogFilter:
    query: str | None = None


@dataclass(slots=True, kw_only=True)
class CatalogSearchInput(SearchInput[CatalogFilter]):
    pass


@dataclass(slots=True, kw_only=True)
class CatalogSearchOutput(SearchOutput[CatalogItem]):
    pass


class CatalogGateway(ABC):
    @abstractmethod
    async def search_items(self, props: CatalogSearchInput) -> CatalogSearchOutput:
        raise NotImplementedError()

    @abstractmethod
    async def get_item(self, external_id: str) -> CatalogItem | None:
        raise NotImplementedError()
