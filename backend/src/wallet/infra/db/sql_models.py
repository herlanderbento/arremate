import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.infra.db.database import Base

if TYPE_CHECKING:
    from account.infra.db.sql_models import UserModel
    from auction.infra.db.sql_models import BidModel, LotModel

MONEY = Numeric(14, 2, asdecimal=True)

FK_USERS_ID = "users.id"
FK_LOTS_ID = "lots.id"
FK_BIDS_ID = "bids.id"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WalletModel(Base):
    __tablename__ = "wallets"
    __table_args__ = (
        CheckConstraint("balance >= 0", name="ck_wallets_balance_non_negative"),
        CheckConstraint("committed >= 0", name="ck_wallets_committed_non_negative"),
        CheckConstraint(
            "committed <= balance",
            name="ck_wallets_committed_within_balance",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(FK_USERS_ID), unique=True, nullable=False
    )
    balance: Mapped[Decimal] = mapped_column(
        MONEY, nullable=False, default=Decimal("0.00"), server_default="0"
    )
    committed: Mapped[Decimal] = mapped_column(
        MONEY, nullable=False, default=Decimal("0.00"), server_default="0"
    )

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="wallet")
    transactions: Mapped[list["WalletTransactionModel"]] = relationship(back_populates="wallet")


class WalletTransactionModel(Base):
    __tablename__ = "wallet_transactions"
    __table_args__ = (
        CheckConstraint(
            "type IN ('DEPOSIT', 'HOLD', 'RELEASE', 'DEBIT', 'CREDIT')",
            name="ck_wallet_transactions_type",
        ),
        CheckConstraint("amount > 0", name="ck_wallet_transactions_amount_positive"),
        Index("idx_wtx_wallet", "wallet_id", text("created_at DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wallets.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    lot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(FK_LOTS_ID), nullable=True
    )
    # SET NULL: a bid deleted by hand must not be blocked by its ledger entries.
    bid_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(FK_BIDS_ID, ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=text("now()")
    )

    wallet: Mapped["WalletModel"] = relationship(back_populates="transactions")
    lot: Mapped["LotModel | None"] = relationship("LotModel")
    bid: Mapped["BidModel | None"] = relationship("BidModel")
