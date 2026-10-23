"""Drives client activity: users add clients, and the driver reads the activity it logged."""

import logging
import re
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from libs.testing.time import eventually
from modules.clients.services.clients import ClientService

ACTIVITY = re.compile(r"client ([0-9a-f-]{36}) was created by (\S+)")


class ActivityDriver:
    def __init__(
        self, clients: ClientService, database: AsyncEngine, logs: pytest.LogCaptureFixture
    ) -> None:
        self.when = _When(clients)
        self.get = _Get(logs)
        self._database = database
        logs.set_level(logging.INFO)

    async def wait_until_subscribed(self) -> None:
        async def subscribed() -> bool:
            async with self._database.connect() as connection:
                found = await connection.execute(
                    text("SELECT 1 FROM events.subscriptions WHERE name = 'log_new_client'")
                )
                return found.first() is not None

        await eventually(subscribed)


class _When:
    def __init__(self, clients: ClientService) -> None:
        self._clients = clients

    async def user_adds_client(self, user_id: str, display_name: str) -> UUID:
        return (await self._clients.create(user_id, display_name, None)).id


class _Get:
    def __init__(self, logs: pytest.LogCaptureFixture) -> None:
        self._logs = logs

    def activity(self) -> list[tuple[str, str]]:
        """Every (client ID, owner) the activity log names, in order."""
        return [(match[1], match[2]) for match in ACTIVITY.finditer(self._logs.text)]

    async def activity_once_it_has(self, count: int) -> list[tuple[str, str]]:
        await eventually(lambda: len(self.activity()) >= count)
        return self.activity()

    def text(self) -> str:
        return self._logs.text
