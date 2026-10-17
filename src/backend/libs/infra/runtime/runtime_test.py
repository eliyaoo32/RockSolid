import asyncio
import os
import signal
from collections.abc import AsyncIterator, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, ClassVar

import httpx
import pytest
from connectrpc.interceptor import MetadataInterceptor
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from libs.infra.cron.cron import CronJob
from libs.infra.events.events import Subscription
from libs.infra.runtime.executables import (
    ASGIApp,
    CronExecutable,
    DomainEventsListenerExecutable,
    HttpExecutable,
    Infra,
    Receive,
    RpcApplication,
    RpcServiceExecutable,
    Scope,
    Send,
)
from libs.infra.runtime.runtime import Runtime, run
from modules.users.services.setup import create_auth

migrated: list[AsyncEngine] = []


async def migrate_shared_schema(database: AsyncEngine) -> None:
    migrated.append(database)


async def pong(scope: Scope, receive: Receive, send: Send) -> None:
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": f"pong {scope['path']}".encode()})


class EchoApi(HttpExecutable):
    migrations = (migrate_shared_schema,)

    def routes(self) -> Mapping[str, ASGIApp]:
        return {"/echo.v1.EchoService": pong}


class Reminders(CronExecutable):
    """A cron executable with two jobs."""

    migrations = (migrate_shared_schema,)

    def jobs(self) -> Sequence[CronJob]:
        return [CronJob("*/5 * * * *", self.send_due), CronJob("0 3 * * *", self.purge_old)]

    async def send_due(self) -> None: ...

    async def purge_old(self) -> None: ...


class Greeted(BaseModel):
    event_type: ClassVar[str] = "tests.Greeted"
    name: str


class Greeters(DomainEventsListenerExecutable):
    """A listener executable with two subscriptions."""

    def subscriptions(self) -> Sequence[Subscription[Any]]:
        return [
            Subscription("welcome_guest", Greeted, self.welcome),
            Subscription("count_guests", Greeted, self.welcome),
        ]

    async def welcome(self, event: Greeted) -> None: ...


class MoreGreeters(DomainEventsListenerExecutable):
    """Reuses a subscription name that Greeters already has."""

    def subscriptions(self) -> Sequence[Subscription[Any]]:
        return [Subscription("welcome_guest", Greeted, self.welcome)]

    async def welcome(self, event: Greeted) -> None: ...


class RecordingBus:
    """An event bus that records the subscriptions it was given and returns once stopped."""

    def __init__(self) -> None:
        self.names: list[str] = []
        self.started = asyncio.Event()

    async def run(self, subscriptions: Sequence[Subscription[Any]], stop: asyncio.Event) -> None:
        self.names = [subscription.name for subscription in subscriptions]
        self.started.set()
        await stop.wait()


class RecordingCron:
    """A cron runner that records the jobs it was given and returns once stopped."""

    def __init__(self) -> None:
        self.jobs: dict[str, str] = {}
        self.started = asyncio.Event()

    async def run(self, jobs: Sequence[CronJob], stop: asyncio.Event) -> None:
        self.jobs = {job.name: job.schedule for job in jobs}
        self.started.set()
        await stop.wait()


class FakeRpcApplication:
    """Stands in for a generated ConnectRPC application."""

    def __init__(self, interceptors: Sequence[MetadataInterceptor[Any]]) -> None:
        self.interceptors = interceptors

    @property
    def path(self) -> str:
        return "/greet.v1.GreetService"

    async def __call__(self, scope: Scope, receive: Receive, send: Send, /) -> None:
        await pong(scope, receive, send)


class GreetApi(RpcServiceExecutable):
    def application(self, interceptors: Sequence[MetadataInterceptor[Any]]) -> RpcApplication:
        return FakeRpcApplication(interceptors)


def now() -> datetime:
    return datetime.now(UTC)


def make_infra(database_url: str) -> Infra:
    return Infra(
        database=create_async_engine(database_url),
        auth=create_auth("rocksolid-test"),
        now=now,
    )


@pytest.fixture
async def infra(database_url: str) -> AsyncIterator[Infra]:
    infra = make_infra(database_url)
    yield infra
    await infra.database.dispose()


async def serving(runtime: Runtime, stop: asyncio.Event) -> asyncio.Task[None]:
    task = asyncio.create_task(runtime.serve(stop))
    async with asyncio.timeout(10):
        while runtime.port is None:
            await asyncio.sleep(0.01)
    return task


async def test_migrates_each_schema_once_without_building_the_executables(infra: Infra) -> None:
    migrated.clear()

    await Runtime([EchoApi, Reminders], infra, port=0).migrate()

    assert migrated == [infra.database]


async def test_serves_routes_and_health_until_stopped(infra: Infra) -> None:
    stop = asyncio.Event()
    runtime = Runtime([EchoApi, GreetApi, Reminders], infra, port=0)
    task = await serving(runtime, stop)

    async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{runtime.port}") as http:
        assert (await http.get("/healthz")).status_code == 200
        assert (await http.get("/readyz")).status_code == 200
        echo = await http.post("/echo.v1.EchoService/Echo")
        assert echo.text == "pong /echo.v1.EchoService/Echo"
        greet = await http.post("/greet.v1.GreetService/Greet")
        assert greet.text == "pong /greet.v1.GreetService/Greet"
        assert (await http.get("/echo.v1.EchoServiceX/Echo")).status_code == 404
        assert (await http.get("/")).status_code == 404

    stop.set()
    await task


def test_signs_in_every_call_of_an_rpc_service(infra: Infra) -> None:
    greet = GreetApi(infra)

    application = greet.routes()["/greet.v1.GreetService"]

    assert isinstance(application, FakeRpcApplication)
    assert application.interceptors == [infra.auth]


async def test_tags_every_response_with_a_request_id(infra: Infra) -> None:
    stop = asyncio.Event()
    runtime = Runtime([EchoApi], infra, port=0)
    task = await serving(runtime, stop)

    async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{runtime.port}") as http:
        new = (await http.get("/healthz")).headers["x-request-id"]
        kept = await http.get("/healthz", headers={"x-request-id": "trace-42"})
        replaced = await http.get("/healthz", headers={"x-request-id": "bad id\twith spaces"})

    assert len(new) == 32
    assert kept.headers["x-request-id"] == "trace-42"
    assert replaced.headers["x-request-id"] != "bad id\twith spaces"
    stop.set()
    await task


@pytest.mark.parametrize(
    "database",
    ["unreachable", "wrong-password"],
)
async def test_is_not_ready_while_the_database_cannot_be_used(
    database: str, database_url: str
) -> None:
    url = (
        "postgresql+asyncpg://nobody:wrong@127.0.0.1:1/none"
        if database == "unreachable"
        else database_url.replace("://test:", "://test:wrong-")
    )
    infra = make_infra(url)
    stop = asyncio.Event()
    runtime = Runtime([EchoApi], infra, port=0)
    task = await serving(runtime, stop)

    async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{runtime.port}") as http:
        assert (await http.get("/healthz")).status_code == 200
        assert (await http.get("/readyz")).status_code == 503

    stop.set()
    await task
    await infra.database.dispose()


async def test_stops_gracefully_on_sigterm(infra: Infra) -> None:
    runtime = Runtime([EchoApi, Reminders], infra, port=0)
    task = await serving(runtime, asyncio.Event())

    os.kill(os.getpid(), signal.SIGTERM)

    async with asyncio.timeout(10):
        await task


@pytest.fixture
def environment(database_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "rocksolid-test")
    monkeypatch.setenv("PORT", "0")


@pytest.mark.usefixtures("environment")
async def test_runs_the_migrate_command_from_environment_configuration() -> None:
    migrated.clear()

    await run(["migrate"], [EchoApi])

    assert len(migrated) == 1


@pytest.mark.usefixtures("environment")
async def test_runs_the_serve_command_until_stopped() -> None:
    stop = asyncio.Event()
    stop.set()

    async with asyncio.timeout(10):
        await run(["serve"], [EchoApi], stop)


async def test_rejects_an_unknown_command() -> None:
    with pytest.raises(SystemExit, match="usage"):
        await run(["deploy"], [EchoApi])


async def test_hands_every_cron_job_to_the_cron_runner(infra: Infra) -> None:
    cron = RecordingCron()
    stop = asyncio.Event()
    task = await serving(Runtime([EchoApi, Reminders], infra, port=0, cron=cron), stop)

    async with asyncio.timeout(10):
        await cron.started.wait()
    stop.set()
    await task

    assert cron.jobs == {"send_due": "*/5 * * * *", "purge_old": "0 3 * * *"}


async def test_hands_every_subscription_to_the_event_bus(infra: Infra) -> None:
    bus = RecordingBus()
    stop = asyncio.Event()
    task = await serving(Runtime([EchoApi, Greeters], infra, port=0, events=bus), stop)

    async with asyncio.timeout(10):
        await bus.started.wait()
    stop.set()
    await task

    assert bus.names == ["welcome_guest", "count_guests"]


async def test_refuses_to_start_with_two_subscriptions_of_the_same_name(infra: Infra) -> None:
    runtime = Runtime([Greeters, MoreGreeters], infra, port=0, events=RecordingBus())

    with pytest.raises(ValueError, match="two subscriptions are named welcome_guest"):
        await runtime.serve(asyncio.Event())


async def test_migrates_the_event_log_that_every_module_publishes_to(infra: Infra) -> None:
    await Runtime([EchoApi], infra, port=0).migrate()

    async with infra.database.connect() as connection:
        found = await connection.execute(text("SELECT to_regclass('events.log')::text"))
        assert found.scalar() == "events.log"
