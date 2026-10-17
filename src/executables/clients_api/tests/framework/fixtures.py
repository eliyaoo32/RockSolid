"""Boots the clients API on a real Postgres, with fake sign-in and a fake clock."""

import asyncio
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime

import pytest
import uvicorn
from clients.v1.clients_connect import ClientsServiceClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

from executables.clients_api.clients_api import create_app, migrate
from executables.clients_api.tests.framework.driver import ClientsDriver, FakeClock
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


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    with PostgresContainer("postgres:18", driver="asyncpg") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
async def driver(database_url: str) -> AsyncIterator[ClientsDriver]:
    engine = create_async_engine(database_url)
    await migrate(engine)
    async with engine.begin() as connection:
        await connection.execute(text("TRUNCATE clients.clients"))
    clock = FakeClock(START)
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(engine, Auth(FakeUsers()), clock),
            host="127.0.0.1",
            port=0,
            log_level="warning",
        )
    )
    serving = asyncio.create_task(server.serve())
    async with asyncio.timeout(10):
        while not server.started:
            await asyncio.sleep(0.01)
    port = server.servers[0].sockets[0].getsockname()[1]
    async with ClientsServiceClient(f"http://127.0.0.1:{port}") as api:
        yield ClientsDriver(api, clock)
    server.should_exit = True
    await serving
    await engine.dispose()
