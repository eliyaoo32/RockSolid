"""Boots client activity through the runtime, on a real Postgres and the real event bus."""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from executables.client_activity.client_activity import ClientActivityExecutable
from executables.client_activity.tests.framework.driver import ActivityDriver
from libs.infra.events.events import PostgresEventBus
from libs.infra.runtime.executables import Infra
from libs.infra.runtime.runtime import Runtime
from libs.testing.time import FakeTime
from modules.clients.services.setup import create_client_service, migrate_schema
from modules.users.services.setup import create_auth

START = datetime(2026, 10, 17, 9, 0, tzinfo=UTC)


@pytest.fixture
async def driver(
    database_url: str, caplog: pytest.LogCaptureFixture
) -> AsyncIterator[ActivityDriver]:
    database = create_async_engine(database_url)
    time = FakeTime(START)
    runtime = Runtime(
        [ClientActivityExecutable],
        Infra(database, create_auth("rocksolid-test"), time),
        port=0,
        events=PostgresEventBus(database, time, time.wait),
    )
    await runtime.migrate()
    await migrate_schema(database)
    stop = asyncio.Event()
    serving = asyncio.create_task(runtime.serve(stop))
    driver = ActivityDriver(create_client_service(database, time), database, caplog)
    await driver.wait_until_subscribed()
    yield driver
    stop.set()
    await serving
    await database.dispose()
