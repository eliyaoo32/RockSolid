"""Drives the users API through its ConnectRPC contract, as a signed-in user would."""

from connectrpc.code import Code
from connectrpc.errors import ConnectError

from users.v1.users_connect import UsersServiceClient
from users.v1.users_pb import GetCurrentUserRequest, User


class UsersDriver:
    def __init__(self, api: UsersServiceClient) -> None:
        self.when = _When(self)
        self.get = _Get(self, api)
        self.token: str | None = None
        self.error: Code | None = None


class _When:
    def __init__(self, driver: UsersDriver) -> None:
        self._driver = driver

    def sign_in_as(self, user_id: str) -> None:
        self._driver.token = f"token-{user_id}"

    def sign_in_with_a_bad_token(self) -> None:
        self._driver.token = "forged"

    def sign_out(self) -> None:
        self._driver.token = None


class _Get:
    def __init__(self, driver: UsersDriver, api: UsersServiceClient) -> None:
        self._driver = driver
        self._api = api

    async def current_user(self) -> User | None:
        """The user the API returns, or None when it fails; `error` then holds its code."""
        headers = (
            {} if self._driver.token is None else {"authorization": f"Bearer {self._driver.token}"}
        )
        self._driver.error = None
        try:
            response = await self._api.get_current_user(GetCurrentUserRequest(), headers=headers)
        except ConnectError as error:
            self._driver.error = error.code
            return None
        return response.user

    def error(self) -> Code | None:
        return self._driver.error
