from decimal import Decimal
from typing import Annotated, Any

from fastapi.encoders import jsonable_encoder
from pydantic import Field, PlainSerializer

from shared.domain.money import canonical

MAX_AMOUNT = Decimal("1000000000.00")

Money = Annotated[Decimal, PlainSerializer(canonical, return_type=str, when_used="json")]

PositiveMoneyInput = Annotated[Decimal, Field(gt=0, le=MAX_AMOUNT, max_digits=14, decimal_places=2)]
MoneyInput = Annotated[Decimal, Field(le=MAX_AMOUNT, max_digits=14, decimal_places=2)]


def to_json(value: Any) -> Any:
    return jsonable_encoder(value, custom_encoder={Decimal: canonical})
