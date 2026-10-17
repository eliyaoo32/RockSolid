"""The clients use cases: what a signed-in user can do with their clients."""

import base64
import binascii
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel

from modules.clients.domain.client import Client
from modules.clients.repositories.client_repository import ClientRepository
from modules.users.domain.user import UserId

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


class ClientNotFoundError(Exception):
    """The owner has no client with this ID."""


class InvalidPageError(Exception):
    """The page size is negative, or the page token is not one this service issued."""


class ClientChanges(BaseModel):
    """The fields to change on a client. Only the fields that are set change."""

    display_name: str = ""
    email: str | None = None


@dataclass(frozen=True)
class ClientsPage:
    clients: list[Client]
    next_page_token: str


class ClientService:
    def __init__(self, repository: ClientRepository, now: Callable[[], datetime]) -> None:
        self._repository = repository
        self._now = now

    async def get(self, owner_id: UserId, client_id: UUID) -> Client:
        client = await self._repository.get(owner_id, client_id)
        if client is None:
            raise ClientNotFoundError
        return client

    async def list(self, owner_id: UserId, page_size: int, page_token: str) -> ClientsPage:
        if page_size < 0:
            raise InvalidPageError
        limit = min(page_size or DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE)
        after = _decode_page_token(page_token) if page_token else None
        # One extra row tells whether another page exists.
        clients = await self._repository.list_newest_first(owner_id, limit + 1, after)
        if len(clients) <= limit:
            return ClientsPage(clients, "")
        last = clients[limit - 1]
        return ClientsPage(clients[:limit], _encode_page_token(last.create_time, last.id))

    async def create(self, owner_id: UserId, display_name: str, email: str | None) -> Client:
        now = self._now()
        client = Client(
            id=uuid4(),
            owner_id=owner_id,
            display_name=display_name,
            email=email,
            create_time=now,
            update_time=now,
        )
        await self._repository.save(client)
        return client

    async def update(self, owner_id: UserId, client_id: UUID, changes: ClientChanges) -> Client:
        client = await self.get(owner_id, client_id)
        for field in changes.model_fields_set:
            setattr(client, field, getattr(changes, field))
        client.update_time = self._now()
        await self._repository.save(client)
        return client

    async def delete(self, owner_id: UserId, client_id: UUID) -> None:
        if not await self._repository.delete(owner_id, client_id):
            raise ClientNotFoundError


def _encode_page_token(create_time: datetime, client_id: UUID) -> str:
    position = json.dumps([create_time.isoformat(), str(client_id)])
    return base64.urlsafe_b64encode(position.encode()).decode()


def _decode_page_token(token: str) -> tuple[datetime, UUID]:
    try:
        create_time, client_id = json.loads(base64.urlsafe_b64decode(token))
        return datetime.fromisoformat(create_time), UUID(client_id)
    except (binascii.Error, ValueError, TypeError) as error:
        raise InvalidPageError from error
