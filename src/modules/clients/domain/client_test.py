from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from modules.clients.domain.client import Client

CREATED = datetime(2026, 10, 17, 9, 0, tzinfo=UTC)


def make_client() -> Client:
    return Client(
        id=uuid4(),
        owner_id="uid-dana",
        display_name="Avi Cohen",
        email="avi@example.com",
        create_time=CREATED,
        update_time=CREATED,
    )


def test_creates_a_client_with_a_trimmed_display_name() -> None:
    client = Client(
        id=uuid4(),
        owner_id="uid-dana",
        display_name="  Avi Cohen  ",
        create_time=CREATED,
        update_time=CREATED,
    )

    assert client.display_name == "Avi Cohen"
    assert client.email is None


@pytest.mark.parametrize("display_name", ["", "   ", "a" * 201])
def test_rejects_an_empty_or_too_long_display_name(display_name: str) -> None:
    with pytest.raises(ValidationError):
        Client(
            id=uuid4(),
            owner_id="uid-dana",
            display_name=display_name,
            create_time=CREATED,
            update_time=CREATED,
        )


def test_rejects_an_invalid_email() -> None:
    with pytest.raises(ValidationError):
        Client(
            id=uuid4(),
            owner_id="uid-dana",
            display_name="Avi Cohen",
            email="not-an-email",
            create_time=CREATED,
            update_time=CREATED,
        )


def test_rejects_a_time_without_a_time_zone() -> None:
    with pytest.raises(ValidationError):
        Client(
            id=uuid4(),
            owner_id="uid-dana",
            display_name="Avi Cohen",
            create_time=datetime(2026, 10, 17, 9, 0),
            update_time=CREATED,
        )


def test_rejects_an_update_time_before_the_create_time() -> None:
    client = make_client()

    with pytest.raises(ValidationError):
        client.update_time = CREATED - timedelta(seconds=1)

    assert client.update_time == CREATED


def test_rejects_an_invalid_change_and_keeps_the_old_value() -> None:
    client = make_client()

    with pytest.raises(ValidationError):
        client.email = "not-an-email"

    assert client.email == "avi@example.com"


@pytest.mark.parametrize(
    ("field", "value"),
    [("id", uuid4()), ("owner_id", "uid-other"), ("create_time", CREATED + timedelta(days=1))],
)
def test_never_changes_its_id_owner_or_create_time(field: str, value: object) -> None:
    client = make_client()
    before = getattr(client, field)

    with pytest.raises(ValidationError):
        setattr(client, field, value)

    assert getattr(client, field) == before
