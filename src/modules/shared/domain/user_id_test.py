import pytest
from pydantic import BaseModel, ValidationError

from modules.shared.domain.user_id import UserId


class Owned(BaseModel):
    owner_id: UserId


def test_accepts_a_user_id() -> None:
    assert Owned(owner_id="x7Yq2LmN9pQrS3tUvW4z").owner_id == "x7Yq2LmN9pQrS3tUvW4z"


@pytest.mark.parametrize("value", ["", "a" * 129])
def test_rejects_an_empty_or_too_long_user_id(value: str) -> None:
    with pytest.raises(ValidationError):
        Owned(owner_id=value)
