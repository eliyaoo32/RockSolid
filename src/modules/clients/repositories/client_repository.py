from datetime import datetime
from typing import Protocol
from uuid import UUID

from modules.clients.domain.client import Client
from modules.users.domain.user import UserId


class ClientRepository(Protocol):
    """Loads and saves clients. Every read and delete is limited to one owner's clients."""

    async def get(self, owner_id: UserId, client_id: UUID) -> Client | None:
        """Returns the owner's client, or None when the owner has no such client."""
        ...

    async def list_newest_first(
        self, owner_id: UserId, limit: int, after: tuple[datetime, UUID] | None
    ) -> list[Client]:
        """Returns up to `limit` of the owner's clients, ordered by (create_time, id),
        newest first, starting after the given (create_time, id)."""
        ...

    async def save(self, client: Client) -> None:
        """Adds the client, or replaces it when it exists."""
        ...

    async def delete(self, owner_id: UserId, client_id: UUID) -> bool:
        """Deletes the owner's client. Returns False when the owner has no such client."""
        ...
