import asyncio
import os
import signal
from collections.abc import AsyncIterator, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from connectrpc.interceptor import MetadataInterceptor
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from libs.infra.runtime.executables import (
    ASGIApp,
    CronSchedulerExecutable,
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


async def migrate_shared_schema(engine: AsyncEngine) -> None:
    migrated.append(engine)


async def pong(scope: Scope, receive: Receive, send: Send) -> None:
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": f"pong {scope['path']}".encode()})


class EchoApi(HttpExecutable):
    migrations = (migrate_shared_schema,)

    def routes(self) -> Mapping[str, ASGIApp]:
        return {"/echo.v1.EchoService": pong}


class Reminders(CronSchedulerExecutable):
    """A background executable: built and accepted, not run yet."""

    migrations = (migrate_shared_schema,)


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


def make_infra(database_url: str) -> Infra:
    return Infra(
        engine=create_async_engine(database_url),
        auth=create_auth("rocksolid-test"),
        now=lambda: datetime.now(UTC),
    )


@pytest.fixture
async def infra(database_url: str) -> AsyncIterator[Infra]:
    infra = make_infra(database_url)
    yield infra
    await infra.engine.dispose()


async def serving(runtime: Runtime, stop: asyncio.Event) -> asyncio.Task[None]:
    task = asyncio.create_task(runtime.serve(stop))
    async with asyncio.timeout(10):
        while runtime.port is None:
            await asyncio.sleep(0.01)
    return task


async def test_migrates_each_schema_once_without_building_the_executables(infra: Infra) -> None:
    migrated.clear()

    await Runtime([EchoApi, Reminders], infra, port=0).migrate()

    assert migrated == [infra.engine]


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
    await infra.engine.dispose()


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
