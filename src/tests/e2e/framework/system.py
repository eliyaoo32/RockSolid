"""Runs the whole system for E2E tests, each part the way it runs in production: every backend
deployable as its own process on one fresh database, and the production frontend build in a
real browser. The deployables run in debug mode, so the debug user signs in, a fake stands in
for the one Firebase Auth call the browser makes, and every fake in `fakes/`, such as the fake
Ollama that answers every agent, stands in for its third party. No request leaves the machine."""

import asyncio
import importlib
import os
import socket
import subprocess
import sys
from collections.abc import Callable, Coroutine, Iterator, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractContextManager, ExitStack, contextmanager
from pathlib import Path
from typing import Protocol
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from playwright.sync_api import BrowserContext, Route
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from e2e.framework.fakes.ollama import FakeOllama
from libs.infra.runtime.executables import Executable
from libs.testing.deployables import every_deployable, http_routes
from libs.testing.time import eventually

# The one user a debug deployable signs in, and the token the browser holds for them.
DEBUG_USER_JWT = "e2e-debug-user-jwt"
DEBUG_USER_NAME = "Dana Levi"
# The debug user's Firebase account, as Firebase Auth describes it. Its name differs from the
# backend's, so a test that sees `DEBUG_USER_NAME` knows the name came from the backend.
DEBUG_USER = {
    "localId": "debug-user",
    "email": "debug-user@example.com",
    "displayName": "Firebase's name",
}
# The web config the frontend is built with for E2E tests (`make e2e-frontend`).
FIREBASE_API_KEY = "e2e-api-key"
# The frontend's origin in the browser. It never reaches DNS: the browser context answers it.
APP_ORIGIN = "http://app.test"
FRONTEND_BUILD = Path("src/tests/e2e/frontend-build")
FAKES = Path(__file__).parent / "fakes"
STARTUP_TIMEOUT = 30


class Fake(Protocol):
    """A running fake of a third party."""

    @property
    def environment(self) -> Mapping[str, str]:
        """The settings that point the deployables at this fake, such as `OLLAMA_BASE_URL`."""
        ...


def every_fake() -> list[Callable[[], AbstractContextManager[Fake]]]:
    """The `serve` of each fake, which runs it. A fake is a module in `fakes/` that is not a test,
    so a project's fake is found without being listed anywhere."""
    return [
        importlib.import_module(f"e2e.framework.fakes.{path.stem}").serve
        for path in sorted(FAKES.glob("*.py"))
        if not path.stem.endswith("_test")
    ]


def _run[T](coroutine: Coroutine[object, object, T]) -> T:
    """Runs an async helper to completion. Playwright's sync API already runs an event loop on
    the test's thread, so the helper runs on its own thread."""
    with ThreadPoolExecutor(max_workers=1) as thread:
        return thread.submit(asyncio.run, coroutine).result()


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _wait_until_up(url: str) -> None:
    def answers() -> bool:
        try:
            return httpx.get(url).is_success
        except httpx.TransportError:
            return False

    _run(eventually(answers, timeout=STARTUP_TIMEOUT))


class Deployable:
    """One backend deployable, run as its own process with the same code and commands as in
    production: `migrate` once, then `serve`."""

    _process: subprocess.Popen[bytes]

    def __init__(
        self,
        name: str,
        executables: Sequence[type[Executable]],
        database_url: str,
        debug: str | None,
        fakes: Mapping[str, str],
    ) -> None:
        self.name = name
        self.routes = http_routes(executables)
        port = _free_port()
        self.url = f"http://127.0.0.1:{port}"
        self._environment = (
            {
                # The test's own interpreter and dependencies run the deployable.
                "PYTHONPATH": os.pathsep.join(sys.path),
                "DATABASE_URL": database_url,
                "FIREBASE_PROJECT_ID": "rocksolid-e2e",
                "DEBUG_USER_JWT": DEBUG_USER_JWT,
                "DEBUG_USER_NAME": DEBUG_USER_NAME,
                # Each agent's debug chat takes a free port, so tests running at once never collide.
                "DEBUG_CHAT_PORT": "0",
                "PORT": str(port),
            }
            | dict(fakes)
            | ({} if debug is None else {"DEBUG": debug})
        )

    def _command(self, command: str) -> list[str]:
        return [sys.executable, "-m", f"deployables.{self.name}.main", command]

    def migrate(self) -> None:
        subprocess.run(self._command("migrate"), env=self._environment, check=True)

    def start(self) -> None:
        self._process = subprocess.Popen(self._command("serve"), env=self._environment)
        _wait_until_up(f"{self.url}/readyz")

    def stop(self) -> None:
        self._process.terminate()
        self._process.wait()


class System:
    """Every deployable, running together on one database."""

    def __init__(self, deployables: Sequence[Deployable], fakes: Sequence[Fake]) -> None:
        self.deployables = deployables
        self.fakes = fakes
        # What every agent's model answered, and what it was told.
        self.ollama = self.fake(FakeOllama)

    def fake[T](self, kind: type[T]) -> T:
        """The running fake of this type, such as `system.fake(FakeOllama)`."""
        return next(fake for fake in self.fakes if isinstance(fake, kind))

    def serving(self, path: str) -> Deployable | None:
        """The deployable that answers `path`, or None when no deployable does."""
        return next(
            (d for d in self.deployables if any(path.startswith(r) for r in d.routes)), None
        )

    def restart(self) -> None:
        """Stops every deployable, then starts them all again, as a release does."""
        for deployable in self.deployables:
            deployable.stop()
        for deployable in self.deployables:
            deployable.start()


async def _create_database(server_url: str) -> str:
    """Creates an empty database on the Postgres server, so each test starts from nothing."""
    name = f"e2e_{uuid4().hex}"
    server = create_async_engine(server_url, isolation_level="AUTOCOMMIT")
    try:
        async with server.connect() as connection:
            await connection.execute(text(f'CREATE DATABASE "{name}"'))
    finally:
        await server.dispose()
    return server_url.rsplit("/", 1)[0] + f"/{name}"


@contextmanager
def running_system(server_url: str, debug: str | None = "true") -> Iterator[System]:
    """Migrates a fresh database with every deployable, and serves them all on it until the
    block ends. `debug` is their `DEBUG` setting, or None to leave it unset; the debug user is
    always set."""
    database_url = _run(_create_database(server_url))
    with ExitStack() as running:
        fakes = [running.enter_context(serve()) for serve in every_fake()]
        environment = {name: value for fake in fakes for name, value in fake.environment.items()}
        system = System(
            [
                Deployable(name, executables, database_url, debug, environment)
                for name, executables in every_deployable().items()
            ],
            fakes,
        )
        for deployable in system.deployables:
            deployable.migrate()
        for deployable in system.deployables:
            deployable.start()
        try:
            yield system
        finally:
            for deployable in system.deployables:
                deployable.stop()


def serve_the_app(context: BrowserContext, system: System) -> None:
    """Answers the browser's requests to the app's origin the way production does: each call to
    a service goes to the deployable that serves it, and every other path gets the frontend
    build, all on one origin. Firebase Auth's account lookup gets the debug user's account, and
    every other request off the origin fails."""

    def answer(route: Route) -> None:
        path = urlsplit(route.request.url).path
        deployable = system.serving(path)
        if deployable is not None:
            route.fulfill(response=route.fetch(url=deployable.url + path))
        else:
            file = FRONTEND_BUILD / path.lstrip("/")
            route.fulfill(path=file if file.is_file() else FRONTEND_BUILD / "index.html")

    # Playwright tries the last route first, so the catch-all goes first.
    context.route("**/*", lambda route: route.abort())
    context.route(f"{APP_ORIGIN}/**", answer)
    context.route(
        "https://identitytoolkit.googleapis.com/v1/accounts:lookup?**",
        lambda route: route.fulfill(json={"users": [DEBUG_USER]}),
    )
