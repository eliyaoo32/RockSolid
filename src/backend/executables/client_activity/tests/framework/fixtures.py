"""Runs client activity through the runtime, on a real Postgres and the real event bus."""

from collections.abc import AsyncIterator

import pytest

from executables.client_activity.client_activity import ClientActivityExecutable
from executables.client_activity.tests.framework.driver import ActivityDriver
from libs.testing.runtime import run_executables
from modules.clients.services.setup import create_client_service, migrate_schema


@pytest.fixture
async def driver(
    database_url: str, caplog: pytest.LogCaptureFixture
) -> AsyncIterator[ActivityDriver]:
    async with run_executables([ClientActivityExecutable], database_url) as running:
        # The listener reads clients' events; the test publishes them by adding clients.
        await migrate_schema(running.database)
        clients = create_client_service(running.database, running.time)
        driver = ActivityDriver(clients, running.database, caplog)
        await driver.wait_until_subscribed()
        yield driver
