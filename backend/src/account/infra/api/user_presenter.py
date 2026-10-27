from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from account.application.use_cases.common.user_output import UserOutput


class UserPresenter(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: EmailStr
    role: str
    created_at: datetime

    @classmethod
    def from_output(cls, output: UserOutput) -> "UserPresenter":
        return cls(
            id=output.id,
            name=output.name,
            email=output.email,
            role=output.role.value,
            created_at=output.created_at,
        )
