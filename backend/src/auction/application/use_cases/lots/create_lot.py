from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from account.domain.user import UserId
from auction.application.use_cases.common.lot_output import LotOutput
from auction.domain.entities.lot import Lot, LotId
from auction.domain.repositories.lot_repository import ILotRepository
from audit.domain.hash_chain import HashChain
from catalog.domain.catalog_gateway import CatalogGateway
from shared.application.clock import Clock, utc_now
from shared.application.use_cases import UseCase
from shared.domain.exceptions import DomainError


@dataclass
class CreateLotInput:
    auctioneer_id: UserId
    external_id: str
    starting_bid: Decimal
    min_increment: Decimal
    starts_at: datetime
    ends_at: datetime


class CreateLotUseCase(UseCase):
    def __init__(
        self,
        lot_repository: ILotRepository,
        catalog: CatalogGateway,
        hash_chain: HashChain,
        clock: Clock = utc_now,
    ):
        self.lot_repository = lot_repository
        self.catalog = catalog
        self.hash_chain = hash_chain
        self.clock = clock

    async def execute(self, input: CreateLotInput) -> LotOutput:
        item = await self.catalog.get_item(input.external_id)
        if item is None:
            raise DomainError(
                "CATALOG_ITEM_NOT_FOUND", "Obra não encontrada no catálogo (ou sem imagem)."
            )

        now = self.clock()
        lot_id = LotId()
        lot = Lot.create(
            id=lot_id,
            auctioneer_id=input.auctioneer_id,
            external_id=item.external_id,
            title=item.title,
            image_url=item.image_url,
            attributes=dict(item.attributes),
            starting_bid=input.starting_bid,
            min_increment=input.min_increment,
            starts_at=input.starts_at,
            ends_at=input.ends_at,
            chain_head=self.hash_chain.chain_head(lot_id.value, 0, None),
            now=now,
        )
        await self.lot_repository.insert(lot)
        return LotOutput.from_entity(lot, now)
