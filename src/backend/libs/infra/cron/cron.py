"""Runs cron jobs. A job says when to run and what to run; a runner triggers it.

`InProcessCronRunner` runs the jobs inside the deployable's process. Another runner, such as a
hosted scheduler, would implement the same `CronRunner` interface, so executables never change.
"""

import asyncio
import logging
from collections.abc import Callable, Coroutine, Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import uuid4

from croniter import croniter

from libs.infra.logs.json_logs import request_id

logger = logging.getLogger(__name__)

type Wait = Callable[[float, asyncio.Event], Coroutine[Any, Any, None]]


class InvalidScheduleError(ValueError):
    """A job's schedule is not a valid cron expression."""


@dataclass(frozen=True)
class CronJob:
    """Runs `run` on a schedule, such as `*/5 * * * *` for every five minutes, in UTC."""

    schedule: str
    run: Callable[[], Coroutine[Any, Any, None]]

    def __post_init__(self) -> None:
        if not croniter.is_valid(self.schedule):
            raise InvalidScheduleError(f"cron job {self.name}: invalid schedule '{self.schedule}'")

    @property
    def name(self) -> str:
        """The job's function name, which its logs use."""
        return self.run.__name__


class CronRunner(Protocol):
    async def run(self, jobs: Sequence[CronJob], stop: asyncio.Event) -> None:
        """Triggers each job on its schedule until `stop` is set."""
        ...


async def wait_or_stop(seconds: float, stop: asyncio.Event) -> None:
    """Waits the given seconds, or less when `stop` is set first."""
    with suppress(TimeoutError):
        await asyncio.wait_for(stop.wait(), timeout=max(seconds, 0))


class InProcessCronRunner:
    """Runs each job in this process, at the times its schedule gives.

    A run that fails is logged, and the job runs again at its next time. A run that takes longer
    than the gap to its next time skips the times it missed.
    """

    def __init__(self, now: Callable[[], datetime], wait: Wait = wait_or_stop) -> None:
        self._now = now
        self._wait = wait

    async def run(self, jobs: Sequence[CronJob], stop: asyncio.Event) -> None:
        async with asyncio.TaskGroup() as tasks:
            for job in jobs:
                tasks.create_task(self._run_on_schedule(job, stop))

    async def _run_on_schedule(self, job: CronJob, stop: asyncio.Event) -> None:
        while not stop.is_set():
            next_time = croniter(job.schedule, self._now()).get_next(datetime)
            await self._wait((next_time - self._now()).total_seconds(), stop)
            if stop.is_set():
                return
            await _run_once(job)


async def _run_once(job: CronJob) -> None:
    # Every run gets its own ID, so its logs can be found together.
    token = request_id.set(f"cron-{job.name}-{uuid4().hex[:12]}")
    try:
        await job.run()
    except Exception:
        logger.exception("cron job %s failed", job.name)
    else:
        logger.info("cron job %s finished", job.name)
    finally:
        request_id.reset(token)
