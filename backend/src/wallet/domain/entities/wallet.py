from dataclasses import dataclass, field
from decimal import Decimal

from account.domain.user import UserId
from auction.domain.entities.bid import BidId
from auction.domain.entities.lot import LotId
from shared.domain.entity import AggregateRoot
from shared.domain.exceptions import DomainError, InvalidArgumentException
from shared.domain.money import ZERO, format_brl, money
from shared.domain.value_objects import Uuid
from wallet.domain.entities.wallet_transaction import WalletTransaction, WalletTransactionType


class WalletId(Uuid):
    pass


MAX_DEPOSIT = Decimal("100000.00")


@dataclass(slots=True, kw_only=True)
class Wallet(AggregateRoot):
    id: WalletId = field(default_factory=WalletId)
    user_id: UserId
    balance: Decimal = ZERO
    committed: Decimal = ZERO

    @property
    def entity_id(self) -> WalletId:
        return self.id

    @property
    def available(self) -> Decimal:
        return self.balance - self.committed

    def deposit(self, amount: Decimal) -> WalletTransaction:
        amount = self._valid_amount(amount, "O valor do depósito deve ser positivo.")
        if amount > MAX_DEPOSIT:
            raise DomainError(
                "DEPOSIT_LIMIT_EXCEEDED",
                f"O depósito máximo é {format_brl(MAX_DEPOSIT)}.",
                {"max_amount": MAX_DEPOSIT},
            )
        self.balance += amount
        return self._entry(WalletTransactionType.DEPOSIT, amount)

    def hold(self, amount: Decimal, lot_id: LotId, bid_id: BidId) -> WalletTransaction:
        amount = self._require_positive(amount)
        if amount > self.available:
            raise DomainError(
                "INSUFFICIENT_BALANCE",
                f"Saldo disponível insuficiente ({format_brl(self.available)} disponível).",
                {"available": self.available},
            )
        self.committed += amount
        return self._entry(WalletTransactionType.HOLD, amount, lot_id, bid_id)

    def release(self, amount: Decimal, lot_id: LotId, bid_id: BidId | None) -> WalletTransaction:
        amount = self._require_positive(amount)
        if amount > self.committed:
            raise InvalidArgumentException("release exceeds committed balance")
        self.committed -= amount
        return self._entry(WalletTransactionType.RELEASE, amount, lot_id, bid_id)

    def debit(self, amount: Decimal, lot_id: LotId) -> WalletTransaction:
        amount = self._require_positive(amount)
        if amount > self.committed:
            raise InvalidArgumentException("debit exceeds committed balance")
        self.committed -= amount
        self.balance -= amount
        return self._entry(WalletTransactionType.DEBIT, amount, lot_id)

    def credit(self, amount: Decimal, lot_id: LotId) -> WalletTransaction:
        amount = self._require_positive(amount)
        self.balance += amount
        return self._entry(WalletTransactionType.CREDIT, amount, lot_id)

    def _entry(
        self,
        type_: WalletTransactionType,
        amount: Decimal,
        lot_id: LotId | None = None,
        bid_id: BidId | None = None,
    ) -> WalletTransaction:
        return WalletTransaction(
            wallet_id=self.id,
            type=type_,
            amount=amount,
            lot_id=lot_id,
            bid_id=bid_id,
        )

    @staticmethod
    def _valid_amount(amount: Decimal, message: str) -> Decimal:
        try:
            amount = money(amount)
        except ValueError as exc:
            raise DomainError(
                "INVALID_AMOUNT", "Valor inválido (use até duas casas decimais)."
            ) from exc
        if amount <= 0:
            raise DomainError("INVALID_AMOUNT", message)
        return amount

    @staticmethod
    def _require_positive(amount: Decimal) -> Decimal:
        amount = money(amount)
        if amount <= 0:
            raise InvalidArgumentException("amount must be positive")
        return amount
