import datetime
from dataclasses import dataclass, field
from enum import Enum

from shared.domain.entity import AggregateRoot
from shared.domain.value_objects import Uuid


class UserRole(str, Enum):
    AUCTIONEER = "AUCTIONEER"
    BIDDER = "BIDDER"


@dataclass
class UserCreateCommand:
    name: str
    role: UserRole
    email: str
    password: str


class UserId(Uuid):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


@dataclass(slots=True, kw_only=True)
class User(AggregateRoot):
    id: UserId = field(default_factory=UserId)
    name: str
    email: str
    password: str
    role: UserRole
    created_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )

    @staticmethod
    def create(command: UserCreateCommand) -> "User":
        return User(
            name=command.name,
            email=normalize_email(command.email),
            password=command.password,
            role=command.role,
        )

    @property
    def entity_id(self) -> UserId:
        return self.id
