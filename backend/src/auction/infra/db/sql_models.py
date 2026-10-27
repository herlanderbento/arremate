import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.infra.db.database import Base

if TYPE_CHECKING:
    from account.infra.db.sql_models import UserModel

MONEY = Numeric(14, 2, asdecimal=True)

FK_USERS_ID = "users.id"
FK_LOTS_ID = "lots.id"
FK_BIDS_ID = "bids.id"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LotModel(Base):
    __tablename__ = "lots"
    __table_args__ = (
        CheckConstraint("starting_bid > 0", name="ck_lots_starting_bid_positive"),
        CheckConstraint("min_increment > 0", name="ck_lots_min_increment_positive"),
        CheckConstraint("ends_at > starts_at", name="ck_lots_ends_after_start"),
        CheckConstraint(
            "status IN ('ACTIVE', 'CANCELLED', 'SETTLED')",
            name="ck_lots_status",
        ),
        Index("idx_lots_showcase", "status", "starts_at", "ends_at"),
        Index("idx_lots_auctioneer", "auctioneer_id"),
        Index(
            "idx_lots_to_settle",
            "ends_at",
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    auctioneer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(FK_USERS_ID), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    starting_bid: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    min_increment: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="ACTIVE", server_default="ACTIVE"
    )
    current_bid: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    leader_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(FK_USERS_ID), nullable=True
    )
    bid_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    chain_head: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=text("now()")
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    auctioneer: Mapped["UserModel"] = relationship("UserModel", foreign_keys=[auctioneer_id])
    leader: Mapped["UserModel | None"] = relationship("UserModel", foreign_keys=[leader_id])
    bids: Mapped[list["BidModel"]] = relationship(
        "BidModel", back_populates="lot", foreign_keys="BidModel.lot_id"
    )
    receipt: Mapped["ReceiptModel | None"] = relationship(
        "ReceiptModel", back_populates="lot", uselist=False
    )


class BidModel(Base):
    __tablename__ = "bids"
    __table_args__ = (
        UniqueConstraint("lot_id", "seq", name="uq_bids_lot_seq"),
        CheckConstraint("seq > 0", name="ck_bids_seq_positive"),
        CheckConstraint("amount > 0", name="ck_bids_amount_positive"),
        Index("idx_bids_bidder", "bidder_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(FK_LOTS_ID), nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    bidder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(FK_USERS_ID), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    prev_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)

    lot: Mapped["LotModel"] = relationship("LotModel", back_populates="bids", foreign_keys=[lot_id])
    bidder: Mapped["UserModel"] = relationship("UserModel", foreign_keys=[bidder_id])


class ReceiptModel(Base):
    __tablename__ = "receipts"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_receipts_amount_positive"),
        Index("idx_receipts_winner", "winner_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(FK_LOTS_ID), unique=True, nullable=False
    )
    winner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(FK_USERS_ID), nullable=False
    )
    winning_bid_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(FK_BIDS_ID, ondelete="SET NULL"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    chain_head: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    public_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=text("now()")
    )

    lot: Mapped["LotModel"] = relationship("LotModel", back_populates="receipt")
    winner: Mapped["UserModel"] = relationship("UserModel", foreign_keys=[winner_id])
    winning_bid: Mapped["BidModel"] = relationship("BidModel", foreign_keys=[winning_bid_id])
