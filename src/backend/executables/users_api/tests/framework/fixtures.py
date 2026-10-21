"""Runs the users API, with fake sign-in, through the runtime."""

from collections.abc import AsyncIterator

import pytest

from executables.users_api.tests.framework.driver import UsersDriver
from executables.users_api.users_api import UsersApiExecutable
from libs.testing.runtime import run_executables
from modules.users.domain.user import User
from modules.users.services.auth import Auth
from modules.users.services.setup import create_auth
from users.v1.users_connect import UsersServiceClient


class FakeUsers:
    """Signs in `token-<user id>`, the tokens the driver sends, in place of Firebase."""

    async def from_token(self, token: str) -> User | None:
        if not token.startswith("token-"):
            return None
        user_id = token.removeprefix("token-")
        return User(id=user_id, email=f"{user_id}@example.com", display_name=user_id)


@pytest.fixture
async def driver(database_url: str) -> AsyncIterator[UsersDriver]:
    async with (
        run_executables([UsersApiExecutable], database_url, auth=Auth(FakeUsers())) as running,
        UsersServiceClient(f"http://127.0.0.1:{running.port}") as api,
    ):
        yield UsersDriver(api)


@pytest.fixture
async def debug_driver(database_url: str) -> AsyncIterator[UsersDriver]:
    """Signs in only the debug user, whose token is `token-debug`, as a debug backend does."""
    auth = create_auth("rocksolid-test", debug_user_jwt="token-debug", debug_user_name="Dana Levi")
    async with (
        run_executables([UsersApiExecutable], database_url, auth=auth) as running,
        UsersServiceClient(f"http://127.0.0.1:{running.port}") as api,
    ):
        yield UsersDriver(api)
