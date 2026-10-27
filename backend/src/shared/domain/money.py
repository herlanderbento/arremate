from decimal import Decimal, InvalidOperation

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value: Decimal | int | str) -> Decimal:
    if isinstance(value, float | bool):
        raise ValueError("monetary amounts must not be float or bool")
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
        quantized = amount.quantize(CENT)
    except InvalidOperation as exc:
        raise ValueError(f"invalid monetary amount: {value!r}") from exc
    if not amount.is_finite() or quantized != amount:
        raise ValueError(f"monetary amounts have at most two decimal places: {value!r}")
    return quantized


def canonical(amount: Decimal) -> str:
    return f"{money(amount):.2f}"


def format_brl(amount: Decimal) -> str:
    amount = money(amount)
    sign = "-" if amount < 0 else ""
    reais, centavos = f"{abs(amount):.2f}".split(".")
    return f"{sign}R$ {int(reais):,}".replace(",", ".") + f",{centavos}"
