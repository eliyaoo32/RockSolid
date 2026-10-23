"""Serves the users ConnectRPC contract: who the signed-in caller is, and the changes they make
to themselves."""

from collections.abc import Sequence

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from connectrpc.request import RequestContext
from pydantic import ValidationError

from libs.infra.runtime.executables import RpcApplication, RpcInterceptor, RpcServiceExecutable
from modules.users.domain.user import User
from modules.users.services.auth import Auth
from modules.users.services.setup import create_user_service, migrate_schema
from modules.users.services.users import UserService
from users.v1 import users_pb as pb
from users.v1.users_connect import UsersService, UsersServiceASGIApplication

NAME_PREFIX = "users/"


class UsersApiExecutable(RpcServiceExecutable):
    """Serves the users contract."""

    migrations = (migrate_schema,)

    def application(self, interceptors: Sequence[RpcInterceptor]) -> RpcApplication:
        users = create_user_service(self.infra.database)
        return UsersServiceASGIApplication(
            UsersApi(self.infra.auth, users), interceptors=interceptors
        )


class UsersApi(UsersService):
    def __init__(self, auth: Auth, users: UserService) -> None:
        self._auth = auth
        self._users = users

    async def get_current_user(
        self,
        request: pb.GetCurrentUserRequest,
        ctx: RequestContext[pb.GetCurrentUserRequest, pb.GetCurrentUserResponse],
        /,
    ) -> pb.GetCurrentUserResponse:
        user = await self._users.current(self._auth.from_ctx(ctx))
        return pb.GetCurrentUserResponse(user=_to_message(user))

    async def update_user(
        self,
        request: pb.UpdateUserRequest,
        ctx: RequestContext[pb.UpdateUserRequest, pb.UpdateUserResponse],
        /,
    ) -> pb.UpdateUserResponse:
        signed_in = self._auth.from_ctx(ctx)
        # The contract checked that the mask names only display_name.
        message = request.user or pb.User()
        if message.name != f"{NAME_PREFIX}{signed_in.id}":
            raise ConnectError(Code.PERMISSION_DENIED, "A user can change only themselves.")
        try:
            user = await self._users.change_display_name(signed_in, message.display_name)
        except ValidationError as error:
            problems = "; ".join(f"user.{p['loc'][0]}: {p['msg']}" for p in error.errors())
            raise ConnectError(Code.INVALID_ARGUMENT, problems) from None
        return pb.UpdateUserResponse(user=_to_message(user))


def _to_message(user: User) -> pb.User:
    return pb.User(name=f"{NAME_PREFIX}{user.id}", display_name=user.display_name, email=user.email)
