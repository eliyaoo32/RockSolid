"""Serves the users ConnectRPC contract: who the signed-in caller is."""

from collections.abc import Sequence

from connectrpc.request import RequestContext

from libs.infra.runtime.executables import RpcApplication, RpcInterceptor, RpcServiceExecutable
from modules.users.services.auth import Auth
from users.v1 import users_pb as pb
from users.v1.users_connect import UsersService, UsersServiceASGIApplication

NAME_PREFIX = "users/"


class UsersApiExecutable(RpcServiceExecutable):
    """Serves the users contract."""

    def application(self, interceptors: Sequence[RpcInterceptor]) -> RpcApplication:
        return UsersServiceASGIApplication(UsersApi(self.infra.auth), interceptors=interceptors)


class UsersApi(UsersService):
    def __init__(self, auth: Auth) -> None:
        self._auth = auth

    async def get_current_user(
        self,
        request: pb.GetCurrentUserRequest,
        ctx: RequestContext[pb.GetCurrentUserRequest, pb.GetCurrentUserResponse],
        /,
    ) -> pb.GetCurrentUserResponse:
        user = self._auth.from_ctx(ctx)
        return pb.GetCurrentUserResponse(
            user=pb.User(
                name=f"{NAME_PREFIX}{user.id}", display_name=user.display_name, email=user.email
            )
        )
