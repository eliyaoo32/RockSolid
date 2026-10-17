"""Boots the clients digest through the runtime, on a real Postgres, with time the test moves."""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from executables.clients_digest.clients_digest import ClientsDigestExecutable
from executables.clients_digest.tests.framework.driver import DigestDriver
from libs.infra.cron.cron import InProcessCronRunner
from libs.infra.runtime.executables import Infra
from libs.infra.runtime.runtime import Runtime
from libs.testing.time import FakeTime
from modules.clients.services.setup import create_client_service
from modules.users.services.setup import create_auth

# A Friday morning, two hours after the 07:00 digest.
START = datetime(2026, 10, 16, 9, 0, tzinfo=UTC)


@pytest.fixture
async def driver(
    database_url: str, caplog: pytest.LogCaptureFixture
) -> AsyncIterator[DigestDriver]:
    database = create_async_engine(database_url)
    time = FakeTime(START)
    infra = Infra(database, create_auth("rocksolid-test"), time)
    runtime = Runtime(
        [ClientsDigestExecutable], infra, port=0, cron=InProcessCronRunner(time, time.wait)
    )
    await runtime.migrate()
    async with database.begin() as connection:
        await connection.execute(text("TRUNCATE clients.clients"))
    stop = asyncio.Event()
    serving = asyncio.create_task(runtime.serve(stop))
    yield DigestDriver(create_client_service(database, time), time, caplog)
    stop.set()
    await serving
    await database.dispose()
