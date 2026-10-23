"""Drives the users API through its ConnectRPC contract, as a signed-in user would."""

from collections.abc import Sequence

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from protobuf.wkt import FieldMask

from users.v1.users_connect import UsersServiceClient
from users.v1.users_pb import GetCurrentUserRequest, UpdateUserRequest, User


class UsersDriver:
    def __init__(self, api: UsersServiceClient) -> None:
        self.when = _When(self, api)
        self.get = _Get(self, api)
        self.token: str | None = None
        self.user_id: str | None = None
        self.error: Code | None = None
        self.changed_user: User | None = None

    def headers(self) -> dict[str, str]:
        return {} if self.token is None else {"authorization": f"Bearer {self.token}"}


class _When:
    def __init__(self, driver: UsersDriver, api: UsersServiceClient) -> None:
        self._driver = driver
        self._api = api

    def sign_in_as(self, user_id: str) -> None:
        self._driver.token = f"token-{user_id}"
        self._driver.user_id = user_id

    def sign_in_with_a_bad_token(self) -> None:
        self._driver.token = "forged"

    def sign_out(self) -> None:
        self._driver.token = None

    async def change_display_name(
        self,
        display_name: str,
        *,
        of: str | None = None,
        paths: Sequence[str] = ("display_name",),
    ) -> None:
        """Changes the display name of the user named `of`, the signed-in user by default, with
        `paths` as the update mask. `get.changed_user()` then holds the answer, or `get.error()`
        the error code."""
        request = UpdateUserRequest(
            user=User(name=of or f"users/{self._driver.user_id}", display_name=display_name),
            update_mask=FieldMask(paths=list(paths)),
        )
        self._driver.error = None
        self._driver.changed_user = None
        try:
            response = await self._api.update_user(request, headers=self._driver.headers())
        except ConnectError as error:
            self._driver.error = error.code
            return
        self._driver.changed_user = response.user


class _Get:
    def __init__(self, driver: UsersDriver, api: UsersServiceClient) -> None:
        self._driver = driver
        self._api = api

    async def current_user(self) -> User | None:
        """The user the API returns, or None when it fails; `error` then holds its code."""
        self._driver.error = None
        try:
            response = await self._api.get_current_user(
                GetCurrentUserRequest(), headers=self._driver.headers()
            )
        except ConnectError as error:
            self._driver.error = error.code
            return None
        return response.user

    def changed_user(self) -> User | None:
        return self._driver.changed_user

    def error(self) -> Code | None:
        return self._driver.error
