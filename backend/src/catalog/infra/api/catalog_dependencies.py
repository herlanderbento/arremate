from functools import lru_cache

from fastapi import Depends

from catalog.application.use_cases.search_catalog_items import SearchCatalogItemsUseCase
from catalog.domain.catalog_gateway import CatalogGateway
from catalog.infra.gateway.artic_catalog_gateway import ArticCatalogGateway
from shared.infra.db.config import settings


@lru_cache
def get_catalog_gateway() -> CatalogGateway:
    return ArticCatalogGateway(
        settings.CATALOG_BASE_URL,
        timeout_seconds=settings.CATALOG_TIMEOUT_SECONDS,
        cache_ttl_seconds=settings.CATALOG_CACHE_TTL_SECONDS,
    )


def get_search_catalog_items_use_case(
    gateway: CatalogGateway = Depends(get_catalog_gateway),
) -> SearchCatalogItemsUseCase:
    return SearchCatalogItemsUseCase(gateway)
