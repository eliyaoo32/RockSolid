"""The facts the clients module publishes. Other modules subscribe to them.

Each event's `event_type` is what the event log stores, so it never changes. Fields are only
ever added, with defaults, so events already in the log still load.
"""

from typing import ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from modules.users.domain.user import UserId


class ClientCreated(BaseModel):
    """A user created a client."""

    model_config = ConfigDict(frozen=True)
    event_type: ClassVar[str] = "clients.ClientCreated"

    client_id: UUID
    owner_id: UserId
    display_name: str
