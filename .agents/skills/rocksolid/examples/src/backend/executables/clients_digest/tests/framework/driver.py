"""Drives the clients digest: adds clients, moves time, and reads the digests it logged."""

import logging
import re
from datetime import timedelta

import pytest

from libs.testing.time import FakeTime, eventually
from modules.clients.services.clients import ClientService

DIGEST = re.compile(r"(\d+) clients were created in the last day")


class DigestDriver:
    def __init__(
        self, clients: ClientService, time: FakeTime, logs: pytest.LogCaptureFixture
    ) -> None:
        self.when = _When(clients, time)
        self.get = _Get(logs)
        logs.set_level(logging.INFO)


class _When:
    def __init__(self, clients: ClientService, time: FakeTime) -> None:
        self._clients = clients
        self._time = time

    async def user_adds_clients(self, user_id: str, *display_names: str) -> None:
        for display_name in display_names:
            await self._clients.create(user_id, display_name, None)

    def time_passes(self, by: timedelta) -> None:
        self._time.advance(by)


class _Get:
    def __init__(self, logs: pytest.LogCaptureFixture) -> None:
        self._logs = logs

    def digests(self) -> list[int]:
        """The client counts of every digest logged so far."""
        return [int(found.group(1)) for found in DIGEST.finditer(self._logs.text)]

    async def digests_once_there_are(self, count: int) -> list[int]:
        await eventually(lambda: len(self.digests()) >= count)
        return self.digests()
