import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.infra.db.database import Base

if TYPE_CHECKING:
    from wallet.infra.db.sql_models import WalletModel

CASCADE_ALL_DELETE_ORPHAN = "all, delete-orphan"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserModel(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('AUCTIONEER', 'BIDDER')",
            name="ck_users_role",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=text("now()")
    )

    wallet: Mapped["WalletModel | None"] = relationship(
        "WalletModel",
        back_populates="user",
        cascade=CASCADE_ALL_DELETE_ORPHAN,
        uselist=False,
    )
