from uuid import UUID

import pytest
from pydantic import ValidationError

from modules.clients.domain.client_tasks import WelcomeClient

AVI = UUID("0f8fad5b-d9cb-469f-a165-70867728950e")


def test_has_a_stable_task_type() -> None:
    assert WelcomeClient.task_type == "clients.WelcomeClient"


def test_survives_the_trip_through_the_task_queue() -> None:
    task = WelcomeClient(client_id=AVI, owner_id="uid-dana")

    assert WelcomeClient.model_validate_json(task.model_dump_json()) == task


def test_never_changes_once_queued() -> None:
    task = WelcomeClient(client_id=AVI, owner_id="uid-dana")

    with pytest.raises(ValidationError):
        task.owner_id = "uid-moshe"  # pyright: ignore[reportAttributeAccessIssue]
