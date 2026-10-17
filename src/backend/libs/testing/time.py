"""Time that moves only when a test moves it."""

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta


class FakeTime:
    """A clock for tests. Pass the object itself as the clock, and `wait` as a cron runner's wait:
    a job then runs exactly when the test moves time past its schedule."""

    def __init__(self, start: datetime) -> None:
        self._now = start
        self._waiting: list[tuple[datetime, asyncio.Event]] = []

    def __call__(self) -> datetime:
        return self._now

    def advance(self, by: timedelta) -> None:
        self._now += by
        for until, reached in self._waiting:
            if until <= self._now:
                reached.set()

    async def wait(self, seconds: float, stop: asyncio.Event) -> None:
        """Returns once the test has moved time `seconds` ahead, or once `stop` is set."""
        reached = asyncio.Event()
        waiting = (self._now + timedelta(seconds=seconds), reached)
        self._waiting.append(waiting)
        tasks = {asyncio.create_task(reached.wait()), asyncio.create_task(stop.wait())}
        try:
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        finally:
            self._waiting.remove(waiting)
            for task in tasks:
                task.cancel()


async def eventually(check: Callable[[], bool], timeout: float = 5) -> None:
    """Waits until `check()` is true, or fails the test after `timeout` seconds."""
    async with asyncio.timeout(timeout):
        while not check():
            await asyncio.sleep(0.01)
