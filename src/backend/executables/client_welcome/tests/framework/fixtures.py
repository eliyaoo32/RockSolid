"""Runs client welcomes through the runtime, on a real Postgres and the real task queue."""

from collections.abc import AsyncIterator

import pytest

from executables.client_welcome.client_welcome import ClientWelcomeExecutable
from executables.client_welcome.tests.framework.driver import WelcomeDriver
from libs.testing.runtime import run_executables
from modules.clients.services.setup import create_client_service, migrate_schema


@pytest.fixture
async def driver(
    database_url: str, caplog: pytest.LogCaptureFixture
) -> AsyncIterator[WelcomeDriver]:
    async with run_executables([ClientWelcomeExecutable], database_url) as running:
        # The consumer runs the clients module's tasks; the test queues them by adding clients.
        await migrate_schema(running.database)
        clients = create_client_service(running.database, running.time)
        yield WelcomeDriver(clients, running.database, caplog)
