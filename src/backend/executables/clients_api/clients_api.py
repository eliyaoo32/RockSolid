"""Serves the clients ConnectRPC contract for signed-in users."""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from uuid import UUID

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from connectrpc.request import RequestContext
from protobuf.wkt import Timestamp
from pydantic import ValidationError

from clients.v1 import clients_pb as pb
from clients.v1.clients_connect import ClientsService, ClientsServiceASGIApplication
from libs.infra.filtering.filtering import InvalidFilterError
from libs.infra.runtime.executables import RpcApplication, RpcInterceptor, RpcServiceExecutable
from modules.clients.domain.client import Client
from modules.clients.services.clients import (
    ClientChanges,
    ClientNotFoundError,
    ClientService,
    InvalidPageError,
)
from modules.clients.services.setup import create_client_service, migrate_schema
from modules.users.services.auth import Auth

NAME_PREFIX = "clients/"


class ClientsApiExecutable(RpcServiceExecutable):
    """Serves the clients contract."""

    migrations = (migrate_schema,)

    def application(self, interceptors: Sequence[RpcInterceptor]) -> RpcApplication:
        clients = create_client_service(self.infra.database, self.infra.now)
        return ClientsServiceASGIApplication(
            ClientsApi(clients, self.infra.auth), interceptors=interceptors
        )


class ClientsApi(ClientsService):
    def __init__(self, clients: ClientService, auth: Auth) -> None:
        self._clients = clients
        self._auth = auth

    async def get_client(
        self,
        request: pb.GetClientRequest,
        ctx: RequestContext[pb.GetClientRequest, pb.GetClientResponse],
        /,
    ) -> pb.GetClientResponse:
        user = self._auth.from_ctx(ctx)
        with _connect_errors():
            client = await self._clients.get(user.id, _client_id(request.name))
        return pb.GetClientResponse(client=_to_message(client))

    async def list_clients(
        self,
        request: pb.ListClientsRequest,
        ctx: RequestContext[pb.ListClientsRequest, pb.ListClientsResponse],
        /,
    ) -> pb.ListClientsResponse:
        user = self._auth.from_ctx(ctx)
        with _connect_errors():
            page = await self._clients.list(
                user.id, request.page_size, request.page_token, request.filter
            )
        return pb.ListClientsResponse(
            clients=[_to_message(client) for client in page.clients],
            next_page_token=page.next_page_token,
        )

    async def create_client(
        self,
        request: pb.CreateClientRequest,
        ctx: RequestContext[pb.CreateClientRequest, pb.CreateClientResponse],
        /,
    ) -> pb.CreateClientResponse:
        user = self._auth.from_ctx(ctx)
        message = request.client or pb.Client()
        email = message.email if message.has_field("email") else None
        with _connect_errors():
            client = await self._clients.create(user.id, message.display_name, email)
        return pb.CreateClientResponse(client=_to_message(client))

    async def update_client(
        self,
        request: pb.UpdateClientRequest,
        ctx: RequestContext[pb.UpdateClientRequest, pb.UpdateClientResponse],
        /,
    ) -> pb.UpdateClientResponse:
        user = self._auth.from_ctx(ctx)
        message = request.client or pb.Client()
        # The contract checked that the mask names only these fields.
        paths = request.update_mask.paths if request.update_mask else []
        values = {
            "display_name": message.display_name,
            "email": message.email if message.has_field("email") else None,
        }
        changes = ClientChanges.model_validate({path: values[path] for path in paths})
        with _connect_errors():
            client = await self._clients.update(user.id, _client_id(message.name), changes)
        return pb.UpdateClientResponse(client=_to_message(client))

    async def delete_client(
        self,
        request: pb.DeleteClientRequest,
        ctx: RequestContext[pb.DeleteClientRequest, pb.DeleteClientResponse],
        /,
    ) -> pb.DeleteClientResponse:
        user = self._auth.from_ctx(ctx)
        with _connect_errors():
            await self._clients.delete(user.id, _client_id(request.name))
        return pb.DeleteClientResponse()


@contextmanager
def _connect_errors() -> Iterator[None]:
    """Turns the module's errors into the Connect error codes the contract promises."""
    try:
        yield
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(map(str, problem['loc']))}: {problem['msg']}" for problem in error.errors()
        )
        raise ConnectError(Code.INVALID_ARGUMENT, problems) from None
    except InvalidFilterError as error:
        fields = ", ".join(error.valid_paths)
        raise ConnectError(
            Code.INVALID_ARGUMENT, f"filter: {error}. Filterable fields: {fields}."
        ) from None
    except ClientNotFoundError:
        raise ConnectError(Code.NOT_FOUND, "The client does not exist.") from None
    except InvalidPageError:
        raise ConnectError(
            Code.INVALID_ARGUMENT,
            "page_token must come from ListClients.",
        ) from None


def _client_id(name: str) -> UUID:
    """The ID in a client's name, which the contract checked looks like clients/<id>."""
    return UUID(name.removeprefix(NAME_PREFIX))


def _to_message(client: Client) -> pb.Client:
    return pb.Client(
        name=f"{NAME_PREFIX}{client.id}",
        display_name=client.display_name,
        email=client.email,
        create_time=Timestamp.from_datetime(client.create_time),
        update_time=Timestamp.from_datetime(client.update_time),
    )
