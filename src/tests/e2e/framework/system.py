"""Runs the whole system for E2E tests, each part the way it runs in production: the backend
deployable as its own process on a fresh database, and the production frontend build in a real
browser. The backend runs in debug mode, so its debug user signs in, and a fake stands in for
the one Firebase Auth call the browser makes. No request leaves the machine."""

import asyncio
import os
import re
import socket
import subprocess
import sys
from collections.abc import Coroutine, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from playwright.sync_api import BrowserContext, Route
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from libs.testing.time import eventually

# The one user a debug backend signs in, and the token the browser holds for them.
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
# Calls to the generated services: `/<package>.v<N>.<Service>/<Method>`.
BACKEND_PATH = re.compile(r"^/\w+\.v\d+\.")
STARTUP_TIMEOUT = 30


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


class Backend:
    """The backend deployable, run as its own process with the same code and commands as in
    production: `migrate` once, then `serve`."""

    _process: subprocess.Popen[bytes]

    def __init__(self, database_url: str, debug: str | None) -> None:
        port = _free_port()
        self.url = f"http://127.0.0.1:{port}"
        self._environment = {
            # The test's own interpreter and dependencies run the deployable.
            "PYTHONPATH": os.pathsep.join(sys.path),
            "DATABASE_URL": database_url,
            "FIREBASE_PROJECT_ID": "rocksolid-e2e",
            "DEBUG_USER_JWT": DEBUG_USER_JWT,
            "DEBUG_USER_NAME": DEBUG_USER_NAME,
            "PORT": str(port),
        } | ({} if debug is None else {"DEBUG": debug})

    def _command(self, command: str) -> list[str]:
        return [sys.executable, "-m", "deployables.backend.main", command]

    def migrate(self) -> None:
        subprocess.run(self._command("migrate"), env=self._environment, check=True)

    def start(self) -> None:
        self._process = subprocess.Popen(self._command("serve"), env=self._environment)
        _wait_until_up(f"{self.url}/readyz")

    def stop(self) -> None:
        self._process.terminate()
        self._process.wait()

    def restart(self) -> None:
        self.stop()
        self.start()


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
def running_backend(server_url: str, debug: str | None = "true") -> Iterator[Backend]:
    """Migrates a fresh database and serves the backend on it until the block ends. `debug` is
    the backend's `DEBUG` setting, or None to leave it unset; the debug user is always set."""
    backend = Backend(_run(_create_database(server_url)), debug)
    backend.migrate()
    backend.start()
    try:
        yield backend
    finally:
        backend.stop()


def serve_the_app(context: BrowserContext, backend: Backend) -> None:
    """Answers the browser's requests to the app's origin the way production does: the frontend
    build and the backend's services, on one origin. Firebase Auth's account lookup gets the
    debug user's account, and every other request off the origin fails."""

    def answer(route: Route) -> None:
        url = urlsplit(route.request.url)
        if BACKEND_PATH.match(url.path):
            route.fulfill(response=route.fetch(url=backend.url + url.path))
        else:
            file = FRONTEND_BUILD / url.path.lstrip("/")
            route.fulfill(path=file if file.is_file() else FRONTEND_BUILD / "index.html")

    # Playwright tries the last route first, so the catch-all goes first.
    context.route("**/*", lambda route: route.abort())
    context.route(f"{APP_ORIGIN}/**", answer)
    context.route(
        "https://identitytoolkit.googleapis.com/v1/accounts:lookup?**",
        lambda route: route.fulfill(json={"users": [DEBUG_USER]}),
    )
