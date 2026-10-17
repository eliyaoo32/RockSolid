from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from modules.shared.domain.user_id import UserId


class Client(BaseModel):
    """A person or business that a user works with, such as a customer."""

    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(frozen=True)
    owner_id: UserId = Field(frozen=True)
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    email: EmailStr | None = None
