"""Runs workers that sleep until a Postgres notification, or a timeout, says there may be work.

The event bus and the task queue both work this way: each worker does one piece of work, then
sleeps until a writer notifies its channel or the time it asked for passes.
"""

import asyncio
from collections.abc import Awaitable, Callable, Sequence

from sqlalchemy.ext.asyncio import AsyncEngine

from libs.infra.cron.cron import Wait

# Does one piece of work and returns how many seconds it may sleep: 0 to work again at once.
type Worker = Callable[[], Awaitable[float]]


async def run_on_notifications(
    database: AsyncEngine,
    channel: str,
    workers: Sequence[Worker],
    wait: Wait,
    stop: asyncio.Event,
) -> None:
    """Runs each worker again and again until `stop` is set. A notification on `channel` wakes
    every sleeping worker."""
    news = [asyncio.Event() for _ in workers]

    def on_notify(*_: object) -> None:
        for new_work in news:
            new_work.set()

    async with database.connect() as listening:
        driver = (await listening.get_raw_connection()).driver_connection
        assert driver is not None, "an open connection always has its driver connection"
        await driver.add_listener(channel, on_notify)
        try:
            async with asyncio.TaskGroup() as tasks:
                for worker, new_work in zip(workers, news, strict=True):
                    tasks.create_task(_work_until_stopped(worker, new_work, wait, stop))
        finally:
            await driver.remove_listener(channel, on_notify)


async def _work_until_stopped(
    worker: Worker, new_work: asyncio.Event, wait: Wait, stop: asyncio.Event
) -> None:
    while not stop.is_set():
        new_work.clear()  # Cleared before working, so a notification during the work is kept.
        seconds = await worker()
        if seconds > 0:
            await _sleep_until_news(new_work, seconds, wait, stop)


async def _sleep_until_news(
    new_work: asyncio.Event, seconds: float, wait: Wait, stop: asyncio.Event
) -> None:
    tasks = {asyncio.create_task(new_work.wait()), asyncio.create_task(wait(seconds, stop))}
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for task in tasks:
            task.cancel()
