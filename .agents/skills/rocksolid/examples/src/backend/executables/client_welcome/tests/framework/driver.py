"""Drives client welcomes: users add and delete clients, the mail API fails when the test says, and
the driver reads the emails the fake mail API was asked to send."""

import logging
from datetime import timedelta
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from e2e.framework.fakes.mail_api import FakeMailApi
from libs.testing.time import FakeTime, eventually
from modules.clients.services.clients import ClientService


class WelcomeDriver:
    def __init__(
        self,
        clients: ClientService,
        mail_api: FakeMailApi,
        database: AsyncEngine,
        time: FakeTime,
        logs: pytest.LogCaptureFixture,
    ) -> None:
        self.when = _When(clients, mail_api, time)
        self.get = _Get(mail_api, database, logs)
        logs.set_level(logging.INFO)


class _When:
    def __init__(self, clients: ClientService, mail_api: FakeMailApi, time: FakeTime) -> None:
        self._clients = clients
        self._mail_api = mail_api
        self._time = time

    async def user_adds_client(self, user_id: str, display_name: str, email: str | None) -> UUID:
        return (await self._clients.create(user_id, display_name, email)).id

    async def user_deletes_client(self, user_id: str, client_id: UUID) -> None:
        await self._clients.delete(user_id, client_id)

    def mail_api_fails_next(self, requests: int) -> None:
        self._mail_api.failures = requests

    def time_passes(self, seconds: float) -> None:
        self._time.advance(timedelta(seconds=seconds))


class _Get:
    def __init__(
        self, mail_api: FakeMailApi, database: AsyncEngine, logs: pytest.LogCaptureFixture
    ) -> None:
        self._mail_api = mail_api
        self._database = database
        self._logs = logs

    def messages(self) -> list[tuple[str, str, dict[str, Any]]]:
        """Every message the mail API took: its path, `Authorization` header, and body."""
        return self._mail_api.messages

    def welcomes(self) -> list[tuple[str, str]]:
        """Every (email address, name) the mail API was asked to welcome, in order."""
        return [(body["to"], body["variables"]["name"]) for _, _, body in self.messages()]

    async def welcomes_once_there_are(self, count: int) -> list[tuple[str, str]]:
        await eventually(lambda: len(self.welcomes()) >= count)
        return self.welcomes()

    async def failed_welcomes_once_there_are(self, count: int) -> int:
        """Waits until `count` welcomes failed at least once and wait for their retry."""
        return await self._count_once_there_are(
            "SELECT count(*) FROM tasks.queue WHERE attempts > 0", count
        )

    async def parked_welcomes_once_there_are(self, count: int) -> int:
        return await self._count_once_there_are("SELECT count(*) FROM tasks.parked", count)

    async def every_task_ran(self) -> bool:
        """True once no task is left in the queue. A task leaves it when its run commits, just
        after its handler returns."""
        await self._count_once_there_are("SELECT count(*) FROM tasks.queue", 0)
        return True

    def text(self) -> str:
        return self._logs.text

    async def _count_once_there_are(self, query: str, count: int) -> int:
        async def counted() -> bool:
            async with self._database.connect() as connection:
                return (await connection.execute(text(query))).scalar_one() == count

        await eventually(counted)
        return count
