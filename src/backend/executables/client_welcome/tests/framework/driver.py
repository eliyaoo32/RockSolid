"""Drives client welcomes: users add clients, and the driver reads the welcomes logged."""

import logging
import re
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from libs.testing.time import eventually
from modules.clients.services.clients import ClientService

WELCOME = re.compile(r"welcomed client ([0-9a-f-]{36}) of (\S+)")


class WelcomeDriver:
    def __init__(
        self, clients: ClientService, database: AsyncEngine, logs: pytest.LogCaptureFixture
    ) -> None:
        self.when = _When(clients)
        self.get = _Get(database, logs)
        logs.set_level(logging.INFO)


class _When:
    def __init__(self, clients: ClientService) -> None:
        self._clients = clients

    async def user_adds_client(self, user_id: str, display_name: str, email: str | None) -> UUID:
        return (await self._clients.create(user_id, display_name, email)).id


class _Get:
    def __init__(self, database: AsyncEngine, logs: pytest.LogCaptureFixture) -> None:
        self._database = database
        self._logs = logs

    def welcomes(self) -> list[tuple[str, str]]:
        """Every (client ID, owner) welcomed so far, in order."""
        return [(match[1], match[2]) for match in WELCOME.finditer(self._logs.text)]

    async def welcomes_once_there_are(self, count: int) -> list[tuple[str, str]]:
        await eventually(lambda: len(self.welcomes()) >= count)
        return self.welcomes()

    async def tasks_waiting(self) -> int:
        async with self._database.connect() as connection:
            return (await connection.execute(text("SELECT count(*) FROM tasks.queue"))).scalar_one()

    def text(self) -> str:
        return self._logs.text
