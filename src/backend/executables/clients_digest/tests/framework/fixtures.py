"""Runs the clients digest through the runtime on a real Postgres, with time the test moves."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from executables.clients_digest.clients_digest import ClientsDigestExecutable
from executables.clients_digest.tests.framework.driver import DigestDriver
from libs.testing.runtime import run_executables
from modules.clients.services.setup import create_client_service

# A Friday morning, two hours after the 07:00 digest.
START = datetime(2026, 10, 16, 9, 0, tzinfo=UTC)


@pytest.fixture
async def driver(
    database_url: str, caplog: pytest.LogCaptureFixture
) -> AsyncIterator[DigestDriver]:
    async with run_executables([ClientsDigestExecutable], database_url, start=START) as running:
        async with running.database.begin() as connection:
            await connection.execute(text("TRUNCATE clients.clients"))
        clients = create_client_service(running.database, running.time)
        yield DigestDriver(clients, running.time, caplog)
