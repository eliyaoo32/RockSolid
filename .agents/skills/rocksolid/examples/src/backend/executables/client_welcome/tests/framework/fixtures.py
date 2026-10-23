"""Runs client welcomes through the runtime, on a real Postgres and the real task queue, with the
clients module's settings pointing it at a fake mail API."""

from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager

import pytest

from e2e.framework.fakes.mail_api import FakeMailApi, serve
from executables.client_welcome.client_welcome import ClientWelcomeExecutable
from executables.client_welcome.tests.framework.driver import WelcomeDriver
from libs.testing.runtime import run_executables
from modules.clients.services.setup import create_client_service


@pytest.fixture
async def driver(
    database_url: str, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[WelcomeDriver]:
    with serve() as mail_api:
        environment = mail_api.environment
        async with _welcomes(database_url, caplog, monkeypatch, mail_api, environment) as d:
            yield d


@pytest.fixture
async def driver_without_mail_api_key(
    database_url: str, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[WelcomeDriver]:
    with serve() as mail_api:
        environment = {"CLIENTS_MAIL_API_URL": mail_api.url}
        async with _welcomes(database_url, caplog, monkeypatch, mail_api, environment) as d:
            yield d


@asynccontextmanager
async def _welcomes(
    database_url: str,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    mail_api: FakeMailApi,
    environment: Mapping[str, str],
) -> AsyncIterator[WelcomeDriver]:
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    async with run_executables([ClientWelcomeExecutable], database_url) as running:
        # The test queues welcomes the way users do: by adding clients.
        clients = create_client_service(running.database, running.time)
        yield WelcomeDriver(clients, mail_api, running.database, running.time, caplog)
