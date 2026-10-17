"""Tells an API who is calling. Every call must be signed in."""

from typing import Any
from weakref import WeakKeyDictionary

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from connectrpc.request import RequestContext

from modules.users.domain.user import User
from modules.users.repositories.user_repository import UserRepository


class Auth:
    """A Connect interceptor that signs in every call, and the source of its caller.

    Register it on the API (`interceptors=[auth]`), then call `auth.from_ctx(ctx)` in handlers.
    """

    def __init__(self, users: UserRepository) -> None:
        self._users = users
        self._callers: WeakKeyDictionary[RequestContext[Any, Any], User] = WeakKeyDictionary()

    def from_ctx(self, ctx: RequestContext[Any, Any]) -> User:
        """Returns the user who made this call."""
        return self._callers[ctx]

    async def on_start(self, ctx: RequestContext[Any, Any]) -> None:
        scheme, _, token = ctx.request_headers.get("authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise ConnectError(Code.UNAUTHENTICATED, "Sign in to call this method.")
        user = await self._users.from_token(token)
        if user is None:
            raise ConnectError(Code.UNAUTHENTICATED, "The sign-in token is invalid.")
        self._callers[ctx] = user

    async def on_end(
        self, token: None, ctx: RequestContext[Any, Any], error: Exception | None, /
    ) -> None:
        """Nothing to clean up: a finished call's context drops out of the weak dictionary."""
