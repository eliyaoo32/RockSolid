from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

UserId = Annotated[str, StringConstraints(min_length=1, max_length=128)]


class User(BaseModel):
    """A person who signs in to the product."""

    model_config = ConfigDict(validate_assignment=True)

    id: UserId = Field(frozen=True)
    email: EmailStr
    display_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
    ]
