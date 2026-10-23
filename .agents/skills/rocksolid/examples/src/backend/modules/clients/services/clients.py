"""The clients use cases: what a signed-in user can do with their clients."""

import base64
import binascii
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from pydantic import BaseModel

from libs.infra.db.transaction import Transaction
from libs.infra.events.events import append_events
from libs.infra.tasks.tasks import enqueue_tasks
from modules.clients.domain.client import Client
from modules.clients.domain.client_events import ClientCreated
from modules.clients.domain.client_tasks import WelcomeClient
from modules.clients.repositories.client_repository import ClientRepository, WelcomeMailer
from modules.clients.services.errors import ClientNotFoundError, InvalidPageError
from modules.users.domain.user import UserId

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


class ClientChanges(BaseModel):
    """The fields to change on a client. Only the fields that are set change."""

    display_name: str = ""
    email: str | None = None


@dataclass(frozen=True)
class ClientsPage:
    clients: list[Client]
    next_page_token: str


class ClientService:
    def __init__(
        self, repository: ClientRepository, mailer: WelcomeMailer, now: Callable[[], datetime]
    ) -> None:
        self._repository = repository
        self._mailer = mailer
        self._now = now

    async def get(self, owner_id: UserId, client_id: UUID) -> Client:
        client = await self._repository.get(owner_id, client_id)
        if client is None:
            raise ClientNotFoundError
        return client

    async def list(
        self, owner_id: UserId, page_size: int, page_token: str, filter: str
    ) -> ClientsPage:
        """Returns up to `page_size` clients, 0 or more, the default page size for 0."""
        limit = min(page_size or DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE)
        after = _decode_page_token(page_token) if page_token else None
        # One extra row tells whether another page exists.
        clients = await self._repository.list_newest_first(owner_id, limit + 1, after, filter)
        if len(clients) <= limit:
            return ClientsPage(clients, "")
        last = clients[limit - 1]
        return ClientsPage(clients[:limit], _encode_page_token(last.create_time, last.id))

    async def count_created_in_the_last_day(self) -> int:
        """Counts the clients every user created in the 24 hours before now."""
        return await self._repository.count_created_since(self._now() - timedelta(days=1))

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
        created = ClientCreated(
            client_id=client.id, owner_id=client.owner_id, display_name=client.display_name
        )
        # Only a client with an email address can be welcomed.
        welcome = [WelcomeClient(client_id=client.id, owner_id=owner_id)] if email else []

        async def publish_creation(transaction: Transaction) -> None:
            await append_events(transaction, [created])
            await enqueue_tasks(transaction, welcome)

        await self._repository.save(client, publish_creation)
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

    async def welcome(self, owner_id: UserId, client_id: UUID) -> None:
        """Sends the client the welcome email, unless the client was deleted or has no email
        address by the time the welcome runs. Raises MailNotConfiguredError when the module's
        settings cannot send email."""
        client = await self._repository.get(owner_id, client_id)
        if client is not None and client.email is not None:
            await self._mailer.send_welcome(client, client.email)


def _encode_page_token(create_time: datetime, client_id: UUID) -> str:
    position = json.dumps([create_time.isoformat(), str(client_id)])
    return base64.urlsafe_b64encode(position.encode()).decode()


def _decode_page_token(token: str) -> tuple[datetime, UUID]:
    try:
        create_time, client_id = json.loads(base64.urlsafe_b64decode(token))
        return datetime.fromisoformat(create_time), UUID(client_id)
    except (binascii.Error, ValueError, TypeError) as error:
        raise InvalidPageError from error
