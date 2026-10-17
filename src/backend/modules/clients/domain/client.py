from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    ValidationInfo,
    field_validator,
)

from modules.users.domain.user import UserId


class Client(BaseModel):
    """A person or business that a user works with, such as a customer."""

    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(frozen=True)
    owner_id: UserId = Field(frozen=True)
    display_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]
    email: EmailStr | None = None
    create_time: AwareDatetime = Field(frozen=True)
    update_time: AwareDatetime

    # A field validator rejects the value before it is set; a model validator runs after.
    @field_validator("update_time")
    @classmethod
    def _updated_after_created(cls, update_time: datetime, info: ValidationInfo) -> datetime:
        create_time = info.data.get("create_time")
        if create_time is not None and update_time < create_time:
            raise ValueError("update_time is before create_time")
        return update_time
