from dataclasses import dataclass

from catalog.application.use_cases.common.catalog_item_output import CatalogItemOutput
from catalog.domain.catalog_gateway import (
    CatalogFilter,
    CatalogGateway,
    CatalogSearchInput,
    CatalogSearchOutput,
)
from shared.application.paginated_list_input import PaginatedListInput
from shared.application.paginated_list_output import PaginatedListOutput
from shared.application.use_cases import UseCase


@dataclass(slots=True)
class SearchCatalogItemsInput(PaginatedListInput[CatalogFilter]):
    pass


@dataclass(slots=True)
class SearchCatalogItemsOutput(PaginatedListOutput[CatalogItemOutput]):
    pass


class SearchCatalogItemsUseCase(UseCase):
    def __init__(self, gateway: CatalogGateway):
        self.gateway = gateway

    async def execute(self, input: SearchCatalogItemsInput) -> SearchCatalogItemsOutput:
        search_input = CatalogSearchInput(**input.to_search_input())
        search_output = await self.gateway.search_items(search_input)
        return self.__to_output(search_output)

    def __to_output(self, search_output: CatalogSearchOutput) -> SearchCatalogItemsOutput:
        items = list(map(CatalogItemOutput.from_entity, search_output.items))
        return SearchCatalogItemsOutput.from_search_output(items, search_output)
