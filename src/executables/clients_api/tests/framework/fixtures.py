"""Boots the clients API through the runtime, on a real Postgres, with fake sign-in and clock."""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from clients.v1.clients_connect import ClientsServiceClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from executables.clients_api.clients_api import ClientsApiExecutable
from executables.clients_api.tests.framework.driver import ClientsDriver, FakeClock
from libs.infra.runtime.executables import Infra
from libs.infra.runtime.runtime import Runtime
from modules.users.domain.user import User
from modules.users.services.auth import Auth

START = datetime(2026, 10, 17, 9, 0, tzinfo=UTC)


class FakeUsers:
    """Signs in `token-<user id>`, the tokens the driver sends, in place of Firebase."""

    async def from_token(self, token: str) -> User | None:
        if not token.startswith("token-"):
            return None
        user_id = token.removeprefix("token-")
        return User(id=user_id, email=f"{user_id}@example.com", display_name=user_id)


@pytest.fixture
async def driver(database_url: str) -> AsyncIterator[ClientsDriver]:
    engine = create_async_engine(database_url)
    clock = FakeClock(START)
    runtime = Runtime([ClientsApiExecutable], Infra(engine, Auth(FakeUsers()), clock), port=0)
    await runtime.migrate()
    async with engine.begin() as connection:
        await connection.execute(text("TRUNCATE clients.clients"))
    stop = asyncio.Event()
    serving = asyncio.create_task(runtime.serve(stop))
    async with asyncio.timeout(10):
        while runtime.port is None:
            await asyncio.sleep(0.01)
    async with ClientsServiceClient(f"http://127.0.0.1:{runtime.port}") as api:
        yield ClientsDriver(api, clock)
    stop.set()
    await serving
    await engine.dispose()
