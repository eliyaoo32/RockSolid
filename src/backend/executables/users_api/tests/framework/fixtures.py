"""Boots the users API through the runtime, with fake sign-in."""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from executables.users_api.tests.framework.driver import UsersDriver
from executables.users_api.users_api import UsersApiExecutable
from libs.infra.runtime.executables import Infra
from libs.infra.runtime.runtime import Runtime
from libs.testing.time import FakeTime
from modules.users.domain.user import User
from modules.users.services.auth import Auth
from users.v1.users_connect import UsersServiceClient


class FakeUsers:
    """Signs in `token-<user id>`, the tokens the driver sends, in place of Firebase."""

    async def from_token(self, token: str) -> User | None:
        if not token.startswith("token-"):
            return None
        user_id = token.removeprefix("token-")
        return User(id=user_id, email=f"{user_id}@example.com", display_name=user_id)


@pytest.fixture
async def driver() -> AsyncIterator[UsersDriver]:
    # The users API stores nothing, so its engine never connects.
    database = create_async_engine("postgresql+asyncpg://unused@localhost/unused")
    runtime = Runtime(
        [UsersApiExecutable],
        Infra(database, Auth(FakeUsers()), FakeTime(datetime(2026, 10, 17, tzinfo=UTC))),
        port=0,
    )
    stop = asyncio.Event()
    serving = asyncio.create_task(runtime.serve(stop))
    async with asyncio.timeout(10):
        while runtime.port is None:
            await asyncio.sleep(0.01)
    async with UsersServiceClient(f"http://127.0.0.1:{runtime.port}") as api:
        yield UsersDriver(api)
    stop.set()
    await serving
    await database.dispose()
