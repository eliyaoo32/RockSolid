import pytest
from pydantic import ValidationError

from modules.users.domain.user import User


def make_user() -> User:
    return User(id="uid-dana", email="dana@example.com", display_name="Dana Levi")


def test_creates_a_user_with_a_trimmed_display_name() -> None:
    user = User(id="uid-dana", email="dana@example.com", display_name="  Dana Levi  ")

    assert user.display_name == "Dana Levi"


@pytest.mark.parametrize("display_name", ["", "   ", "a" * 101])
def test_rejects_an_empty_or_too_long_display_name(display_name: str) -> None:
    with pytest.raises(ValidationError):
        User(id="uid-dana", email="dana@example.com", display_name=display_name)


def test_rejects_an_invalid_email() -> None:
    with pytest.raises(ValidationError):
        User(id="uid-dana", email="not-an-email", display_name="Dana Levi")


def test_rejects_an_invalid_change_and_keeps_the_old_value() -> None:
    user = make_user()

    with pytest.raises(ValidationError):
        user.display_name = ""

    assert user.display_name == "Dana Levi"


def test_never_changes_its_id() -> None:
    user = make_user()

    with pytest.raises(ValidationError):
        user.id = "uid-other"

    assert user.id == "uid-dana"


@pytest.mark.parametrize("user_id", ["", "a" * 129])
def test_rejects_an_empty_or_too_long_user_id(user_id: str) -> None:
    with pytest.raises(ValidationError):
        User(id=user_id, email="dana@example.com", display_name="Dana Levi")
