from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

from account.domain.user import UserRole
from catalog.application.use_cases.common.catalog_item_output import CatalogItemOutput
from catalog.application.use_cases.search_catalog_items import (
    SearchCatalogItemsInput,
    SearchCatalogItemsOutput,
    SearchCatalogItemsUseCase,
)
from catalog.domain.catalog_gateway import CatalogFilter
from catalog.infra.api.catalog_dependencies import get_search_catalog_items_use_case
from shared.infra.api.auth_dependencies import require_role
from shared.infra.api.presenter import CollectionPresenter, meta_from_output

router = APIRouter(prefix="/catalog", tags=["Catalog"])


class CatalogItemPresenter(BaseModel):
    external_id: str
    title: str
    image_url: str
    attributes: dict[str, str]

    @classmethod
    def from_output(cls, o: CatalogItemOutput) -> "CatalogItemPresenter":
        return cls(
            external_id=o.external_id,
            title=o.title,
            image_url=o.image_url,
            attributes=o.attributes,
        )


class CatalogSearchPresenter(CollectionPresenter[CatalogItemPresenter]):
    @classmethod
    def from_output(cls, o: SearchCatalogItemsOutput) -> "CatalogSearchPresenter":
        return cls(
            data=[CatalogItemPresenter.from_output(i) for i in o.items],
            meta=meta_from_output(o),
        )


@router.get(
    "/search",
    response_model=CatalogSearchPresenter,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.AUCTIONEER))],
)
async def search_catalog(
    filter_query: str = Query(min_length=2, max_length=100, alias="filter"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=12, ge=1, le=100),
    use_case: SearchCatalogItemsUseCase = Depends(get_search_catalog_items_use_case),
):
    output = await use_case.execute(
        SearchCatalogItemsInput(
            page=page,
            per_page=per_page,
            filter=CatalogFilter(query=filter_query),
        )
    )
    return CatalogSearchPresenter.from_output(output)
