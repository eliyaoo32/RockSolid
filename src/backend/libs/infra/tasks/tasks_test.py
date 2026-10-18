import asyncio
import logging
from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

import pytest
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from libs.infra.logs.json_logs import request_id
from libs.infra.retry.retry import Constant, NonRetryableError
from libs.infra.tasks.tasks import (
    PostgresTaskQueue,
    TaskHandler,
    enqueue_tasks,
    migrate_task_queue,
)
from libs.testing.time import FakeTime, eventually

START = datetime(2026, 10, 17, 9, 0, tzinfo=UTC)


class SendInvite(BaseModel):
    model_config = ConfigDict(frozen=True)
    task_type: ClassVar[str] = "tests.SendInvite"
    name: str


class PrintBadge(BaseModel):
    model_config = ConfigDict(frozen=True)
    task_type: ClassVar[str] = "tests.PrintBadge"
    name: str


class Untyped(BaseModel):
    """Has no task_type, so it is not a task."""


class Handled:
    """Records what each handler ran, and fails on the names it is told to fail on."""

    def __init__(self) -> None:
        self.invites: list[str] = []
        self.badges: list[str] = []
        self.request_ids: list[str | None] = []
        self.failing: set[str] = set()
        self.attempts = 0
        self.started = asyncio.Event()

    async def send_invite(self, task: SendInvite) -> None:
        self.attempts += 1
        if task.name in self.failing:
            raise RuntimeError(f"cannot invite {task.name}")
        self.invites.append(task.name)
        self.request_ids.append(request_id.get())

    async def print_badge(self, task: PrintBadge) -> None:
        self.badges.append(task.name)

    async def refuse_invite(self, task: SendInvite) -> None:
        self.attempts += 1
        raise NonRetryableError(f"{task.name} has no address")

    async def crash_while_inviting(self, task: SendInvite) -> None:
        self.started.set()
        await asyncio.Event().wait()  # Runs until the test crashes its consumer.


class Queue:
    def __init__(self, database: AsyncEngine) -> None:
        self.database = database
        self.time = FakeTime(START)
        self.handled = Handled()
        self.stop = asyncio.Event()
        self.consumers: list[asyncio.Task[None]] = []

    def handlers(self) -> Sequence[TaskHandler[Any]]:
        return [
            TaskHandler(SendInvite, self.handled.send_invite),
            TaskHandler(PrintBadge, self.handled.print_badge),
        ]

    def start(self, handlers: Sequence[TaskHandler[Any]] | None = None) -> asyncio.Task[None]:
        consumer = asyncio.create_task(
            PostgresTaskQueue(self.database, self.time, self.time.wait).run(
                handlers or self.handlers(), self.stop
            )
        )
        self.consumers.append(consumer)
        return consumer

    async def enqueue(self, *tasks: BaseModel) -> None:
        async with self.database.begin() as connection:
            await enqueue_tasks(connection, tasks)

    async def rows(self, query: str) -> list[tuple[object, ...]]:
        async with self.database.connect() as connection:
            return [tuple(row) for row in await connection.execute(text(query))]


@pytest.fixture
async def queue(database_url: str) -> AsyncIterator[Queue]:
    database = create_async_engine(database_url)
    await migrate_task_queue(database)
    async with database.begin() as connection:
        await connection.execute(text("TRUNCATE tasks.queue, tasks.parked RESTART IDENTITY"))
    queue = Queue(database)
    yield queue
    queue.stop.set()
    for consumer in queue.consumers:
        if not consumer.cancelled():
            await consumer
    await database.dispose()


async def test_runs_each_task_once_with_the_handler_of_its_type(queue: Queue) -> None:
    await queue.enqueue(SendInvite(name="before start"))
    queue.start()

    await queue.enqueue(SendInvite(name="Avi"), PrintBadge(name="Noa"), SendInvite(name="Dana"))

    await eventually(lambda: len(queue.handled.invites) == 3 and queue.handled.badges == ["Noa"])
    assert queue.handled.invites == ["before start", "Avi", "Dana"]

    async def queue_is_empty() -> bool:
        return await queue.rows("SELECT id FROM tasks.queue") == []

    await eventually(queue_is_empty)  # A task is gone once it ran, when its transaction commits.


async def test_never_runs_a_task_whose_transaction_rolled_back(queue: Queue) -> None:
    queue.start()

    with pytest.raises(RuntimeError, match="saving failed"):
        async with queue.database.begin() as connection:
            await enqueue_tasks(connection, [SendInvite(name="rolled back")])
            raise RuntimeError("saving failed")
    await queue.enqueue(SendInvite(name="Avi"))

    await eventually(lambda: queue.handled.invites == ["Avi"])


async def test_retries_a_failing_task_with_backoff_while_other_tasks_run(queue: Queue) -> None:
    queue.start()
    queue.handled.failing.add("Avi")

    await queue.enqueue(SendInvite(name="Avi"), SendInvite(name="Noa"))
    await eventually(lambda: queue.handled.invites == ["Noa"])
    assert queue.handled.attempts == 2

    queue.time.advance(timedelta(seconds=1))
    await queue.enqueue(SendInvite(name="Dana"))  # Wakes the consumer before the retry is due.
    await eventually(lambda: queue.handled.invites == ["Noa", "Dana"])
    assert queue.handled.attempts == 3, "no retry before the backoff ends"

    queue.handled.failing.clear()
    queue.time.advance(timedelta(seconds=1))

    await eventually(lambda: queue.handled.invites == ["Noa", "Dana", "Avi"])


async def test_parks_a_task_once_its_retry_strategy_stops(
    queue: Queue, caplog: pytest.LogCaptureFixture
) -> None:
    queue.start([TaskHandler(SendInvite, queue.handled.send_invite, Constant(30, attempts=2))])
    queue.handled.failing.add("Avi")

    with caplog.at_level(logging.WARNING):
        await queue.enqueue(SendInvite(name="Avi"))
        await eventually(lambda: queue.handled.attempts == 1)
        queue.time.advance(timedelta(seconds=30))

        async def parked() -> bool:
            return len(await queue.rows("SELECT id FROM tasks.parked")) == 1

        await eventually(parked)

    assert queue.handled.attempts == 2
    parked_task = await queue.rows(
        "SELECT id, type, payload->>'name', attempts, error FROM tasks.parked"
    )
    assert parked_task[0][:4] == (1, "tests.SendInvite", "Avi", 2)
    assert "cannot invite Avi" in str(parked_task[0][4])
    assert await queue.rows("SELECT id FROM tasks.queue") == []
    assert "task 1 of type tests.SendInvite parked after 2 attempts" in caplog.text


async def test_parks_at_once_when_the_handler_says_retrying_cannot_help(queue: Queue) -> None:
    queue.start([TaskHandler(SendInvite, queue.handled.refuse_invite)])

    await queue.enqueue(SendInvite(name="Avi"))

    async def parked() -> bool:
        return len(await queue.rows("SELECT id FROM tasks.parked")) == 1

    await eventually(parked)
    assert queue.handled.attempts == 1, "never retried"


async def test_runs_each_task_once_when_a_deployable_runs_twice(queue: Queue) -> None:
    queue.start()
    queue.start()

    await queue.enqueue(*(SendInvite(name=f"guest {n}") for n in range(20)))

    await eventually(lambda: len(queue.handled.invites) == 20)
    assert sorted(queue.handled.invites) == sorted(f"guest {n}" for n in range(20))


async def test_runs_a_task_again_when_its_consumer_crashed_while_running_it(queue: Queue) -> None:
    crashing = queue.start([TaskHandler(SendInvite, queue.handled.crash_while_inviting)])
    await queue.enqueue(SendInvite(name="Avi"))
    await queue.handled.started.wait()

    crashing.cancel()
    with pytest.raises(asyncio.CancelledError):
        await crashing
    queue.start()

    await eventually(lambda: queue.handled.invites == ["Avi"])


async def test_runs_a_task_under_the_request_id_that_queued_it(queue: Queue) -> None:
    queue.start()
    token = request_id.set("req-77")
    try:
        await queue.enqueue(SendInvite(name="Avi"))
    finally:
        request_id.reset(token)

    await eventually(lambda: queue.handled.request_ids == ["req-77"])


def test_rejects_a_handler_for_a_model_without_a_task_type() -> None:
    async def handle(task: Untyped) -> None: ...

    with pytest.raises(TypeError, match="Untyped has no task_type"):
        TaskHandler(Untyped, handle)


async def test_refuses_to_queue_a_model_without_a_task_type(queue: Queue) -> None:
    with pytest.raises(TypeError, match="Untyped has no task_type"):
        await queue.enqueue(Untyped())


async def test_queuing_no_tasks_writes_nothing(queue: Queue) -> None:
    await queue.enqueue()

    assert await queue.rows("SELECT id FROM tasks.queue") == []
