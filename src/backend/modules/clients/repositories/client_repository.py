from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from modules.clients.domain.client import Client
from modules.clients.domain.client_events import ClientCreated
from modules.clients.domain.client_tasks import WelcomeClient
from modules.users.domain.user import UserId


class ClientRepository(Protocol):
    """Loads and saves clients. Every read and delete is limited to one owner's clients."""

    async def get(self, owner_id: UserId, client_id: UUID) -> Client | None:
        """Returns the owner's client, or None when the owner has no such client."""
        ...

    async def list_newest_first(
        self, owner_id: UserId, limit: int, after: tuple[datetime, UUID] | None, filter: str
    ) -> list[Client]:
        """Returns up to `limit` of the owner's clients that match the OData filter (all of them
        when it is empty), ordered by (create_time, id), newest first, starting after the given
        (create_time, id). Raises InvalidFilterError for an invalid filter."""
        ...

    async def count_created_since(self, since: datetime) -> int:
        """Returns how many clients, of every owner, were created at or after `since`."""
        ...

    async def save(
        self,
        client: Client,
        events: Sequence[ClientCreated] = (),
        tasks: Sequence[WelcomeClient] = (),
    ) -> None:
        """Adds the client, or replaces it when it exists, publishes the events, and queues the
        tasks, all in one transaction: all are saved, or none is."""
        ...

    async def delete(self, owner_id: UserId, client_id: UUID) -> bool:
        """Deletes the owner's client. Returns False when the owner has no such client."""
        ...
