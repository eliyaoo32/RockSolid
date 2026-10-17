import asyncio
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest

from libs.infra.cron.cron import CronJob, InProcessCronRunner, InvalidScheduleError, wait_or_stop
from libs.infra.logs.json_logs import request_id
from libs.testing.time import FakeTime, eventually

START = datetime(2026, 10, 17, 9, 2, tzinfo=UTC)


class Running:
    """A cron runner running in the background, with time the test moves."""

    def __init__(self) -> None:
        self.time = FakeTime(START)
        self.stop = asyncio.Event()
        self.runs: list[tuple[str, datetime]] = []
        self.failures = 0

    async def send_reminders(self) -> None:
        self.runs.append(("send_reminders", self.time()))

    async def purge(self) -> None:
        self.runs.append(("purge", self.time()))

    async def fail(self) -> None:
        self.failures += 1
        raise RuntimeError(f"the mail server is down, run {request_id.get()}")


@pytest.fixture
async def running() -> AsyncIterator[Running]:
    running = Running()
    jobs = [
        CronJob("*/5 * * * *", running.send_reminders),
        CronJob("0 10 * * *", running.purge),
        CronJob("*/30 * * * *", running.fail),
    ]
    task = asyncio.create_task(
        InProcessCronRunner(running.time, running.time.wait).run(jobs, running.stop)
    )
    yield running
    running.stop.set()
    await task


async def test_runs_each_job_when_time_reaches_its_schedule(running: Running) -> None:
    running.time.advance(timedelta(minutes=2))
    await asyncio.sleep(0)
    assert running.runs == []

    running.time.advance(timedelta(minutes=1))
    await eventually(lambda: len(running.runs) == 1)
    running.time.advance(timedelta(minutes=5))
    await eventually(lambda: len(running.runs) == 2)

    assert running.runs == [
        ("send_reminders", START.replace(minute=5)),
        ("send_reminders", START.replace(minute=10)),
    ]


async def test_runs_several_jobs_side_by_side(running: Running) -> None:
    running.time.advance(timedelta(minutes=58))

    await eventually(lambda: ("purge", START.replace(hour=10, minute=0)) in running.runs)


async def test_logs_a_failed_run_and_runs_the_job_again_next_time(
    running: Running, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO):
        running.time.advance(timedelta(minutes=28))
        await eventually(lambda: running.failures == 1)
        running.time.advance(timedelta(minutes=30))
        await eventually(lambda: running.failures == 2)

    assert caplog.text.count("cron job fail failed") == 2
    assert "cron job send_reminders finished" in caplog.text
    assert "run cron-fail-" in caplog.text, "each run has its own ID"
    assert request_id.get() is None


async def test_stops_before_a_job_runs() -> None:
    running = Running()
    running.stop.set()
    jobs = [CronJob("* * * * *", running.send_reminders)]

    await InProcessCronRunner(running.time, running.time.wait).run(jobs, running.stop)

    assert running.runs == []


@pytest.mark.parametrize("schedule", ["every minute", "61 * * * *", ""])
def test_rejects_an_invalid_schedule(schedule: str) -> None:
    async def send() -> None: ...

    with pytest.raises(InvalidScheduleError, match="cron job send: invalid schedule"):
        CronJob(schedule, send)


async def test_waits_until_the_time_passes_or_stop_is_set() -> None:
    stop = asyncio.Event()

    async with asyncio.timeout(1):
        await wait_or_stop(0, stop)
        stop.set()
        await wait_or_stop(3600, stop)
