"""Drives the clients API through its ConnectRPC contract, as a signed-in user would."""

from collections.abc import Awaitable, Callable
from datetime import timedelta

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from protobuf.wkt import FieldMask

from clients.v1.clients_connect import ClientsServiceClient
from clients.v1.clients_pb import (
    Client,
    CreateClientRequest,
    DeleteClientRequest,
    GetClientRequest,
    ListClientsRequest,
    UpdateClientRequest,
)
from libs.testing.time import FakeTime


class ClientsDriver:
    def __init__(self, api: ClientsServiceClient, clock: FakeTime) -> None:
        self.when = _When(self, api, clock)
        self.get = _Get(self, api)
        self.token: str | None = None
        self.last: Client | None = None
        self.next_page_token = ""
        self.error: Code | None = None
        self.error_message = ""

    def headers(self) -> dict[str, str]:
        return {} if self.token is None else {"authorization": f"Bearer {self.token}"}

    async def call[T](self, request: Callable[[], Awaitable[T]]) -> T | None:
        """Runs one RPC and records its error code, or None when it succeeded."""
        self.error = None
        try:
            return await request()
        except ConnectError as error:
            self.error = error.code
            self.error_message = error.message
            return None


class _When:
    def __init__(self, driver: ClientsDriver, api: ClientsServiceClient, clock: FakeTime) -> None:
        self._driver = driver
        self._api = api
        self._clock = clock

    def sign_in_as(self, user_id: str) -> None:
        self._driver.token = f"token-{user_id}"

    def sign_in_with_a_bad_token(self) -> None:
        self._driver.token = "forged"

    def sign_out(self) -> None:
        self._driver.token = None

    def time_passes(self, by: timedelta) -> None:
        self._clock.advance(by)

    async def create_client(self, display_name: str, email: str | None = None) -> None:
        request = CreateClientRequest(client=Client(display_name=display_name, email=email))
        response = await self._driver.call(
            lambda: self._api.create_client(request, headers=self._driver.headers())
        )
        if response is not None:
            self._driver.last = response.client

    async def update_client(
        self, name: str, paths: list[str], display_name: str = "", email: str | None = None
    ) -> None:
        request = UpdateClientRequest(
            client=Client(name=name, display_name=display_name, email=email),
            update_mask=FieldMask(paths=paths),
        )
        response = await self._driver.call(
            lambda: self._api.update_client(request, headers=self._driver.headers())
        )
        if response is not None:
            self._driver.last = response.client

    async def delete_client(self, name: str) -> None:
        await self._driver.call(
            lambda: self._api.delete_client(
                DeleteClientRequest(name=name), headers=self._driver.headers()
            )
        )


class _Get:
    def __init__(self, driver: ClientsDriver, api: ClientsServiceClient) -> None:
        self._driver = driver
        self._api = api

    def error(self) -> Code | None:
        return self._driver.error

    def error_message(self) -> str:
        return self._driver.error_message

    def last_client(self) -> Client:
        assert self._driver.last is not None
        return self._driver.last

    def next_page_token(self) -> str:
        return self._driver.next_page_token

    async def client(self, name: str) -> Client | None:
        response = await self._driver.call(
            lambda: self._api.get_client(
                GetClientRequest(name=name), headers=self._driver.headers()
            )
        )
        return None if response is None else response.client

    async def client_names(
        self, page_size: int = 0, page_token: str = "", filter: str = ""
    ) -> list[str] | None:
        """Returns the display names on one page, and keeps the next page token."""
        request = ListClientsRequest(page_size=page_size, page_token=page_token, filter=filter)
        response = await self._driver.call(
            lambda: self._api.list_clients(request, headers=self._driver.headers())
        )
        if response is None:
            return None
        self._driver.next_page_token = response.next_page_token
        return [client.display_name for client in response.clients]
