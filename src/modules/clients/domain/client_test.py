from uuid import uuid4

import pytest
from pydantic import ValidationError

from modules.clients.domain.client import Client


def make_client() -> Client:
    return Client(id=uuid4(), owner_id="uid-dana", name="Avi Cohen", email="avi@example.com")


def test_creates_a_client_with_a_trimmed_name() -> None:
    client = Client(id=uuid4(), owner_id="uid-dana", name="  Avi Cohen  ")

    assert client.name == "Avi Cohen"
    assert client.email is None


@pytest.mark.parametrize("name", ["", "   ", "a" * 201])
def test_rejects_an_empty_or_too_long_name(name: str) -> None:
    with pytest.raises(ValidationError):
        Client(id=uuid4(), owner_id="uid-dana", name=name)


def test_rejects_an_invalid_email() -> None:
    with pytest.raises(ValidationError):
        Client(id=uuid4(), owner_id="uid-dana", name="Avi Cohen", email="not-an-email")


def test_rejects_an_invalid_change_and_keeps_the_old_value() -> None:
    client = make_client()

    with pytest.raises(ValidationError):
        client.email = "not-an-email"

    assert client.email == "avi@example.com"


@pytest.mark.parametrize("field", ["id", "owner_id"])
def test_never_changes_its_id_or_owner(field: str) -> None:
    client = make_client()
    before = getattr(client, field)

    with pytest.raises(ValidationError):
        setattr(client, field, uuid4() if field == "id" else "uid-other")

    assert getattr(client, field) == before
