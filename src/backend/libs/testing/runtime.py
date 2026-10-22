"""Runs executables in a test the way a deployable runs them: through the real runtime, with
fakes in place of the outside world and time that moves only when the test moves it."""

import asyncio
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic_ai import models
from pydantic_ai.models.test import TestModel
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from libs.infra.cron.cron import InProcessCronRunner
from libs.infra.events.events import PostgresEventBus
from libs.infra.llm.models import ConfiguredModels, Models
from libs.infra.runtime.executables import AgentExecutable, Executable, Infra
from libs.infra.runtime.runtime import DebugChat, Runtime
from libs.infra.tasks.tasks import PostgresTaskQueue
from libs.testing.models import FakeModels
from libs.testing.time import FakeTime, eventually
from modules.users.services.auth import Auth
from modules.users.services.setup import create_auth

# A Saturday morning, so tests read the same whatever day they run.
START = datetime(2026, 10, 17, 9, 0, tzinfo=UTC)
# The deployable's settings without an Ollama API key: an agent that asks for a real model fails.
NO_MODELS = ConfiguredModels("http://never-connected", None)

# No test reaches a real model; an agent runs on a test model the test passes in.
models.ALLOW_MODEL_REQUESTS = False


@dataclass(frozen=True)
class RunningExecutables:
    database: AsyncEngine
    time: FakeTime
    port: int
    # Each agent's debug chat port, by agent name, when the test asked for debug chats.
    debug_chat_ports: dict[str, int]


@asynccontextmanager
async def run_executables(
    executables: Sequence[type[Executable]],
    database_url: str,
    *,
    auth: Auth | None = None,
    models: Models = NO_MODELS,
    debug_chat: DebugChat | None = None,
    start: datetime = START,
) -> AsyncIterator[RunningExecutables]:
    """Migrates and serves the executables until the block ends.

    Cron jobs, event and task retries, and conversations follow the returned `time`. Pass `auth`
    to sign callers in with a fake; without it, every call is unauthenticated. Pass `models`, such
    as `FakeModels(FunctionModel(...))`, for agents to run on, and `debug_chat` to serve each
    agent's debug chat.
    """
    database = create_async_engine(database_url)
    time = FakeTime(start)
    runtime = Runtime(
        executables,
        Infra(database, auth or create_auth("rocksolid-test"), time, models),
        port=0,
        cron=InProcessCronRunner(time, time.wait),
        events=PostgresEventBus(database, time, time.wait),
        tasks=PostgresTaskQueue(database, time, time.wait),
        debug_chat=debug_chat,
    )
    try:
        await runtime.migrate()
        stop = asyncio.Event()
        serving = asyncio.create_task(runtime.serve(stop))
        debug_chats = (
            0 if debug_chat is None else sum(issubclass(e, AgentExecutable) for e in executables)
        )
        await eventually(
            lambda: (runtime.port is not None and len(runtime.debug_chat_ports) == debug_chats)
            or serving.done()
        )
        if serving.done():
            await serving  # Raises why the executables could not start.
        assert runtime.port is not None
        yield RunningExecutables(database, time, runtime.port, runtime.debug_chat_ports)
        stop.set()
        await serving
    finally:
        await database.dispose()


def build_executables(executables: Sequence[type[Executable]]) -> list[Executable]:
    """Builds the executables the way the runtime does, on a database that is never connected
    to, for a test that reads what they declare, such as their task handlers."""
    database = create_async_engine("postgresql+asyncpg://never-connected@localhost/none")
    infra = Infra(database, create_auth("rocksolid-test"), FakeTime(START), FakeModels(TestModel()))
    return [create(infra) for create in executables]
