import datetime
from dataclasses import dataclass
from uuid import UUID

from account.domain.user import User, UserRole


@dataclass(frozen=True)
class UserOutput:
    id: UUID
    name: str
    email: str
    role: UserRole
    created_at: datetime.datetime

    @classmethod
    def from_entity(cls, user: User) -> "UserOutput":
        return cls(
            id=user.id.value,
            name=user.name,
            email=user.email,
            role=user.role,
            created_at=user.created_at,
        )
