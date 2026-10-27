from decimal import Decimal as D

import pytest

from account.domain.user import UserId
from auction.domain.entities.bid import BidId
from auction.domain.entities.lot import LotId
from shared.domain.exceptions import DomainError
from shared.domain.money import canonical, format_brl, money
from wallet.domain.entities.wallet import MAX_DEPOSIT, Wallet
from wallet.domain.entities.wallet_transaction import WalletTransactionType


def _wallet(balance="0.00", committed="0.00") -> Wallet:
    return Wallet(user_id=UserId(), balance=D(balance), committed=D(committed))


def test_format_brl():
    assert format_brl(D("1050.00")) == "R$ 1.050,00"
    assert format_brl(D("0.05")) == "R$ 0,05"
    assert format_brl(D("1234567.89")) == "R$ 1.234.567,89"
    assert format_brl(D("1000000000")) == "R$ 1.000.000.000,00"


def test_money_is_exact_and_refuses_extra_precision():
    assert money(D("10")) == D("10.00") and str(money("10.5")) == "10.50"
    assert money(1) == D("1.00")
    assert canonical(D("1050")) == canonical(D("1050.00")) == "1050.00"
    for bad in (D("10.005"), "1e-3", "abc", D("NaN"), D("Infinity"), 0.1, True):
        with pytest.raises(ValueError):
            money(bad)


def test_decimal_arithmetic_has_no_float_drift():
    wallet = _wallet()
    for _ in range(10):
        wallet.deposit(D("0.10"))
    wallet.deposit(D("0.20"))

    assert wallet.balance == D("1.20")  # with floats: 1.2000000000000002


def test_deposit_adds_to_balance_and_returns_entry():
    wallet = _wallet(balance="10.00")

    entry = wallet.deposit(D("5.50"))

    assert wallet.balance == D("15.50")
    assert (entry.type, entry.amount, entry.wallet_id) == (
        WalletTransactionType.DEPOSIT,
        D("5.50"),
        wallet.id,
    )


@pytest.mark.parametrize("amount", [D("0"), D("-0.01"), D("10.001")])
def test_deposit_must_be_positive_with_two_decimals(amount):
    with pytest.raises(DomainError) as exc:
        _wallet().deposit(amount)
    assert exc.value.code == "INVALID_AMOUNT"


def test_deposit_has_a_cap():
    assert MAX_DEPOSIT == D("100000.00")
    _wallet().deposit(MAX_DEPOSIT)

    with pytest.raises(DomainError) as exc:
        _wallet().deposit(MAX_DEPOSIT + D("0.01"))
    assert exc.value.code == "DEPOSIT_LIMIT_EXCEEDED"
    assert exc.value.details == {"max_amount": MAX_DEPOSIT}
    assert "R$ 100.000,00" in exc.value.message


def test_hold_only_within_available_balance():
    wallet = _wallet(balance="10.00", committed="6.00")

    with pytest.raises(DomainError) as exc:
        wallet.hold(D("4.01"), LotId(), BidId())
    assert exc.value.code == "INSUFFICIENT_BALANCE"
    assert exc.value.details == {"available": D("4.00")}
    assert "R$ 4,00" in exc.value.message

    wallet.hold(D("4.00"), LotId(), BidId())
    assert (wallet.committed, wallet.available) == (D("10.00"), D("0.00"))


def test_release_returns_committed_to_available():
    wallet = _wallet(balance="10.00", committed="7.00")

    wallet.release(D("7.00"), LotId(), BidId())

    assert (wallet.balance, wallet.available) == (D("10.00"), D("10.00"))


def test_debit_and_credit_on_settlement():
    winner, auctioneer = _wallet(balance="10.00", committed="7.25"), _wallet()

    winner.debit(D("7.25"), LotId())
    auctioneer.credit(D("7.25"), LotId())

    assert (winner.balance, winner.committed) == (D("2.75"), D("0.00"))
    assert auctioneer.balance == D("7.25")
