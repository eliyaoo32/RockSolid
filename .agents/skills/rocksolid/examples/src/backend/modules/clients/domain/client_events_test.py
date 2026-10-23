from uuid import UUID

import pytest
from pydantic import ValidationError

from modules.clients.domain.client_events import ClientCreated

AVI = UUID("0f8fad5b-d9cb-469f-a165-70867728950e")


def test_has_a_stable_event_type() -> None:
    assert ClientCreated.event_type == "clients.ClientCreated"


def test_survives_the_trip_through_the_event_log() -> None:
    event = ClientCreated(client_id=AVI, owner_id="uid-dana", display_name="Avi Cohen")

    assert ClientCreated.model_validate_json(event.model_dump_json()) == event


def test_never_changes_once_published() -> None:
    event = ClientCreated(client_id=AVI, owner_id="uid-dana", display_name="Avi Cohen")

    with pytest.raises(ValidationError):
        event.display_name = "Someone else"  # pyright: ignore[reportAttributeAccessIssue]
