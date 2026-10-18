"""Runs a deployable's executables in one process: builds the shared infra once, migrates the
module schemas, serves every HTTP executable on one server, runs every cron job, event
subscription, and task handler, and stops gracefully on SIGTERM."""

import asyncio
import re
import signal
from collections.abc import Iterable, MutableMapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from typing import Any
from uuid import uuid4

import uvicorn
from pydantic_settings import BaseSettings
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine

from libs.infra.cron.cron import CronJob, CronRunner, InProcessCronRunner
from libs.infra.events.events import EventBus, PostgresEventBus, Subscription, migrate_event_log
from libs.infra.logs.json_logs import configure_logging, request_id
from libs.infra.runtime.executables import (
    CronExecutable,
    DomainEventsListenerExecutable,
    Executable,
    HttpExecutable,
    Infra,
    Receive,
    Scope,
    Send,
    TasksConsumerExecutable,
)
from libs.infra.tasks.tasks import (
    PostgresTaskQueue,
    TaskHandler,
    TaskQueue,
    migrate_task_queue,
    task_type_of,
)
from modules.users.services.setup import create_auth

USAGE = "usage: <deployable> migrate | serve"
REQUEST_ID_HEADER = b"x-request-id"
# A caller's request ID is kept only when it is short and plain, so it is safe to log.
VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")


class InfraSettings(BaseSettings):
    """The configuration every deployable reads from its environment variables."""

    # postgresql+asyncpg://<user>:<password>@<host>:5432/<database>
    database_url: str
    # The Firebase project whose ID tokens sign users in.
    firebase_project_id: str
    port: int = 8080
    # Proxies trusted to set X-Forwarded-For and X-Forwarded-Proto, such as a load balancer.
    forwarded_allow_ips: str = "127.0.0.1"


@dataclass(frozen=True)
class _BackgroundWork:
    jobs: Sequence[CronJob]
    subscriptions: Sequence[Subscription[Any]]
    handlers: Sequence[TaskHandler[Any]]


def _collect_background_work(executables: Sequence[Executable]) -> _BackgroundWork:
    """Collects the executables' cron jobs, subscriptions, and task handlers. Raises ValueError
    when two subscriptions share a name, since a name keeps one place in the event log, or when
    two handlers take one task type, since only one may run it."""
    work = _BackgroundWork(
        jobs=[j for e in executables if isinstance(e, CronExecutable) for j in e.jobs()],
        subscriptions=[
            s
            for e in executables
            if isinstance(e, DomainEventsListenerExecutable)
            for s in e.subscriptions()
        ],
        handlers=[
            h for e in executables if isinstance(e, TasksConsumerExecutable) for h in e.handlers()
        ],
    )
    if repeated := _repeated(s.name for s in work.subscriptions):
        raise ValueError(f"two subscriptions are named {repeated}")
    if repeated := _repeated(task_type_of(h.task) for h in work.handlers):
        raise ValueError(f"two handlers take {repeated}")
    return work


def _repeated(names: Iterable[str]) -> str:
    """The names that appear more than once, comma-separated, or "" when none do."""
    names = list(names)
    return ", ".join(sorted({name for name in names if names.count(name) > 1}))


async def run(
    argv: Sequence[str], executables: Sequence[type[Executable]], stop: asyncio.Event | None = None
) -> None:
    """The deployable's entry point: `migrate` or `serve`, configured from the environment."""
    command = argv[0] if argv else ""
    if command not in ("migrate", "serve"):
        raise SystemExit(USAGE)
    configure_logging()
    # Settings reads its required fields from the environment, which Pyright cannot see.
    settings = InfraSettings()  # pyright: ignore[reportCallIssue]
    now = partial(datetime.now, UTC)
    infra = Infra(
        database=create_async_engine(settings.database_url, pool_pre_ping=True),
        auth=create_auth(settings.firebase_project_id),
        now=now,
    )
    runtime = Runtime(
        executables,
        infra,
        settings.port,
        settings.forwarded_allow_ips,
    )
    try:
        if command == "migrate":
            await runtime.migrate()
        else:
            await runtime.serve(stop or asyncio.Event())
    finally:
        await infra.database.dispose()


class Runtime:
    def __init__(
        self,
        executables: Sequence[type[Executable]],
        infra: Infra,
        port: int,
        forwarded_allow_ips: str = "127.0.0.1",
        cron: CronRunner | None = None,
        events: EventBus | None = None,
        tasks: TaskQueue | None = None,
    ) -> None:
        self._executable_classes = executables
        self._infra = infra
        self._port = port
        self._forwarded_allow_ips = forwarded_allow_ips
        # Runs every cron job in this process; a test can pass a runner driven by fake time.
        self._cron = cron or InProcessCronRunner(infra.now)
        # Delivers every domain event subscription; a test can pass a bus driven by fake time.
        self._events = events or PostgresEventBus(infra.database, infra.now)
        # Runs every task handler; a test can pass a queue driven by fake time.
        self._tasks = tasks or PostgresTaskQueue(infra.database, infra.now)
        self._http: list[HttpExecutable] = []
        self._server: uvicorn.Server | None = None

    @property
    def port(self) -> int | None:
        """The port the server listens on, once it has started."""
        if self._server is None or not self._server.started:
            return None
        return self._server.servers[0].sockets[0].getsockname()[1]

    async def migrate(self) -> None:
        """Migrates the event log and the task queue, which every module may write to, then
        every schema the executables need, each once, without building them."""
        await migrate_event_log(self._infra.database)
        await migrate_task_queue(self._infra.database)
        migrations = {m: None for e in self._executable_classes for m in e.migrations}
        for migration in migrations:
            await migration(self._infra.database)

    async def serve(self, stop: asyncio.Event) -> None:
        """Serves the HTTP executables until `stop` is set or the process gets SIGTERM or SIGINT."""
        executables = [create(self._infra) for create in self._executable_classes]
        self._http = [e for e in executables if isinstance(e, HttpExecutable)]
        work = _collect_background_work(executables)
        loop = asyncio.get_running_loop()
        for signal_number in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(signal_number, stop.set)
        self._server = uvicorn.Server(
            uvicorn.Config(
                self._app,
                interface="asgi3",  # uvicorn cannot tell from a bound method.
                host="0.0.0.0",
                port=self._port,
                proxy_headers=True,
                forwarded_allow_ips=self._forwarded_allow_ips,
                log_config=None,  # Logs go through the JSON logging the runtime configured.
                timeout_graceful_shutdown=30,
            )
        )
        try:
            async with asyncio.TaskGroup() as tasks:
                tasks.create_task(self._serve_http(stop))
                if work.jobs:
                    tasks.create_task(self._cron.run(work.jobs, stop))
                if work.subscriptions:
                    tasks.create_task(self._events.run(work.subscriptions, stop))
                if work.handlers:
                    tasks.create_task(self._tasks.run(work.handlers, stop))
        finally:
            for signal_number in (signal.SIGTERM, signal.SIGINT):
                loop.remove_signal_handler(signal_number)

    async def _serve_http(self, stop: asyncio.Event) -> None:
        assert self._server is not None
        serving = asyncio.create_task(self._server.serve())
        stopping = asyncio.create_task(stop.wait())
        await asyncio.wait({serving, stopping}, return_when=asyncio.FIRST_COMPLETED)
        self._server.should_exit = True  # Finishes running requests, then stops.
        stop.set()  # The server can also stop on its own, on a signal it caught itself.
        stopping.cancel()
        await serving

    async def _app(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await _complete_lifespan(receive, send)
            return
        current_request = _request_id(scope)
        token = request_id.set(current_request)

        async def send_with_request_id(message: MutableMapping[str, Any]) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = [
                    *message.get("headers", []),
                    (REQUEST_ID_HEADER, current_request.encode()),
                ]
            await send(message)

        try:
            await self._route(scope, receive, send_with_request_id)
        finally:
            request_id.reset(token)

    async def _route(self, scope: Scope, receive: Receive, send: Send) -> None:
        path: str = scope["path"]
        if path == "/healthz":
            await _respond(send, 200, b"ok")
            return
        if path == "/readyz":
            ready = await self._database_reachable()
            await _respond(
                send, 200 if ready else 503, b"ready" if ready else b"database unreachable"
            )
            return
        for executable in self._http:
            for prefix, app in executable.routes().items():
                if path.startswith(f"{prefix}/"):
                    await app(scope, receive, send)
                    return
        await _respond(send, 404, b"not found")

    async def _database_reachable(self) -> bool:
        try:
            async with self._infra.database.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except (OSError, SQLAlchemyError):
            return False
        return True


def _request_id(scope: Scope) -> str:
    """The caller's X-Request-ID when it is safe to log, or a new one."""
    for name, value in scope.get("headers", []):
        if name == REQUEST_ID_HEADER and VALID_REQUEST_ID.fullmatch(value.decode("latin-1")):
            return value.decode("latin-1")
    return uuid4().hex


async def _complete_lifespan(receive: Receive, send: Send) -> None:
    """Answers the server's startup and shutdown events; executables need neither."""
    while True:
        message = await receive()
        if message["type"] == "lifespan.startup":
            await send({"type": "lifespan.startup.complete"})
        else:
            await send({"type": "lifespan.shutdown.complete"})
            return


async def _respond(send: Send, status: int, body: bytes) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"text/plain")],
        }
    )
    await send({"type": "http.response.body", "body": body})
