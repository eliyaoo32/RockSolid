"""The work the clients module asks for. Each task has one handler, in one executable.

Each task's `task_type` is what the task queue stores, so it never changes. Fields are only
ever added, with defaults, so tasks already in the queue still load.
"""

from typing import ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from modules.users.domain.user import UserId


class WelcomeClient(BaseModel):
    """Welcome a new client who has an email address."""

    model_config = ConfigDict(frozen=True)
    task_type: ClassVar[str] = "clients.WelcomeClient"

    client_id: UUID
    owner_id: UserId
