"""Runs executables in a test the way a deployable runs them: through the real runtime, with
fakes in place of the outside world and time that moves only when the test moves it."""

import asyncio
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from libs.infra.cron.cron import InProcessCronRunner
from libs.infra.events.events import PostgresEventBus
from libs.infra.runtime.executables import Executable, Infra
from libs.infra.runtime.runtime import Runtime
from libs.testing.time import FakeTime, eventually
from modules.users.services.auth import Auth
from modules.users.services.setup import create_auth

# A Saturday morning, so tests read the same whatever day they run.
START = datetime(2026, 10, 17, 9, 0, tzinfo=UTC)


@dataclass(frozen=True)
class RunningExecutables:
    database: AsyncEngine
    time: FakeTime
    port: int


@asynccontextmanager
async def run_executables(
    executables: Sequence[type[Executable]],
    database_url: str,
    *,
    auth: Auth | None = None,
    start: datetime = START,
) -> AsyncIterator[RunningExecutables]:
    """Migrates and serves the executables until the block ends.

    Cron jobs and event retries follow the returned `time`. Pass `auth` to sign callers in with
    a fake; without it, every RPC call is unauthenticated.
    """
    database = create_async_engine(database_url)
    time = FakeTime(start)
    runtime = Runtime(
        executables,
        Infra(database, auth or create_auth("rocksolid-test"), time),
        port=0,
        cron=InProcessCronRunner(time, time.wait),
        events=PostgresEventBus(database, time, time.wait),
    )
    try:
        await runtime.migrate()
        stop = asyncio.Event()
        serving = asyncio.create_task(runtime.serve(stop))
        await eventually(lambda: runtime.port is not None or serving.done())
        if serving.done():
            await serving  # Raises why the executables could not start.
        assert runtime.port is not None
        yield RunningExecutables(database, time, runtime.port)
        stop.set()
        await serving
    finally:
        await database.dispose()
