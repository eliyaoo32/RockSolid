"""Time that moves only when a test moves it."""

import asyncio
from collections.abc import Awaitable, Callable
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

    async def wait(self, until: datetime, stop: asyncio.Event) -> None:
        """Returns once the test has moved time to `until`, or once `stop` is set. A time already
        passed returns at once."""
        if until <= self._now:
            return
        reached = asyncio.Event()
        waiting = (until, reached)
        self._waiting.append(waiting)
        tasks = {asyncio.create_task(reached.wait()), asyncio.create_task(stop.wait())}
        try:
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        finally:
            self._waiting.remove(waiting)
            for task in tasks:
                task.cancel()


async def eventually(check: Callable[[], bool | Awaitable[bool]], timeout: float = 5) -> None:
    """Waits until `check()` is true, or fails the test after `timeout` seconds. The check may
    be async, such as a database query."""
    async with asyncio.timeout(timeout):
        while True:
            result = check()
            if await result if isinstance(result, Awaitable) else result:
                return
            await asyncio.sleep(0.01)
