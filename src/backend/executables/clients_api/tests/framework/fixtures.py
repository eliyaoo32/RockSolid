"""Runs the clients API, with fake sign-in, through the runtime on a real Postgres."""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text

from clients.v1.clients_connect import ClientsServiceClient
from executables.clients_api.clients_api import ClientsApiExecutable
from executables.clients_api.tests.framework.driver import ClientsDriver
from libs.testing.runtime import START, run_executables
from libs.testing.users import fake_auth

__all__ = ["START", "driver"]


@pytest.fixture
async def driver(database_url: str) -> AsyncIterator[ClientsDriver]:
    async with run_executables([ClientsApiExecutable], database_url, auth=fake_auth()) as running:
        async with running.database.begin() as connection:
            await connection.execute(text("TRUNCATE clients.clients"))
        async with ClientsServiceClient(f"http://127.0.0.1:{running.port}") as api:
            yield ClientsDriver(api, running.time)
