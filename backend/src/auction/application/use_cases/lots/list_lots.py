from dataclasses import dataclass
from datetime import datetime

from auction.application.use_cases.common.lot_output import LotOutput
from auction.domain.repositories.lot_repository import (
    ILotRepository,
    LotFilter,
    LotSearchInput,
    LotSearchOutput,
)
from shared.application.clock import Clock, utc_now
from shared.application.paginated_list_input import PaginatedListInput
from shared.application.paginated_list_output import PaginatedListOutput
from shared.application.use_cases import UseCase


@dataclass(slots=True)
class ListLotsInput(PaginatedListInput[LotFilter]):
    pass


@dataclass(slots=True)
class ListLotsOutput(PaginatedListOutput[LotOutput]):
    pass


class ListLotsUseCase(UseCase):
    def __init__(self, lot_repository: ILotRepository, clock: Clock = utc_now):
        self.lot_repository = lot_repository
        self.clock = clock

    async def execute(self, input: ListLotsInput) -> ListLotsOutput:
        now = self.clock()
        search_output = await self.lot_repository.search(
            LotSearchInput(now=now, **input.to_search_input())
        )
        return self.__to_output(search_output, now)

    def __to_output(self, search_output: LotSearchOutput, now: datetime) -> ListLotsOutput:
        items = [LotOutput.from_entity(lot, now) for lot in search_output.items]
        return ListLotsOutput.from_search_output(items, search_output)
