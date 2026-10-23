"""Tells an API or an agent who is calling."""

from typing import Any
from weakref import WeakKeyDictionary

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from connectrpc.request import RequestContext

from modules.users.domain.user import User
from modules.users.repositories.user_repository import SignInProvider


class SignInFailedError(Exception):
    """The caller sent sign-in credentials that are malformed or not valid."""


class Auth:
    """Signs callers in, and is the Connect interceptor that signs in every call of an API.

    Register it on the API (`interceptors=[auth]`), then call `auth.from_ctx(ctx)` in handlers.
    """

    def __init__(self, users: SignInProvider) -> None:
        self._users = users
        self._callers: WeakKeyDictionary[RequestContext[Any, Any], User] = WeakKeyDictionary()

    async def sign_in(self, authorization: str | None) -> User | None:
        """Returns who an `Authorization` header signs in, or None when there is no header.
        Raises SignInFailedError when the header is not a valid `Bearer` token."""
        if not authorization:
            return None
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise SignInFailedError("The sign-in header is not a Bearer token.")
        user = await self._users.from_token(token)
        if user is None:
            raise SignInFailedError("The sign-in token is invalid.")
        return user

    def from_ctx(self, ctx: RequestContext[Any, Any]) -> User:
        """Returns the user who made this call."""
        return self._callers[ctx]

    async def on_start(self, ctx: RequestContext[Any, Any]) -> None:
        try:
            user = await self.sign_in(ctx.request_headers.get("authorization"))
        except SignInFailedError as error:
            raise ConnectError(Code.UNAUTHENTICATED, str(error)) from error
        if user is None:
            raise ConnectError(Code.UNAUTHENTICATED, "Sign in to call this method.")
        self._callers[ctx] = user

    async def on_end(
        self, token: None, ctx: RequestContext[Any, Any], error: Exception | None, /
    ) -> None:
        """Nothing to clean up: a finished call's context drops out of the weak dictionary."""
