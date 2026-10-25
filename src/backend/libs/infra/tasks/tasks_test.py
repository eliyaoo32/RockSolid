import asyncio
import logging
from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

import pytest
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from libs.infra.events.events import PostgresEventBus, Subscription, migrate_event_log
from libs.infra.logs.json_logs import request_id
from libs.infra.retry.retry import Constant, NonRetryableError
from libs.infra.tasks.tasks import (
    PostgresTaskQueue,
    TaskHandler,
    TaskRejectedError,
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


class InviteRefused(BaseModel):
    model_config = ConfigDict(frozen=True)
    event_type: ClassVar[str] = "tests.InviteRefused"
    name: str
    reason: str


class Untyped(BaseModel):
    """Has no task_type and no event_type, so it is neither a task nor a domain event."""


class Handled:
    """Records what each handler ran, and fails on the names it is told to fail on."""

    def __init__(self) -> None:
        self.invites: list[str] = []
        self.badges: list[str] = []
        self.request_ids: list[str | None] = []
        self.failing: set[str] = set()
        self.attempts = 0
        self.started = asyncio.Event()
        self.refusals: list[InviteRefused] = []

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

    async def reject_invite(self, task: SendInvite) -> None:
        self.attempts += 1
        raise TaskRejectedError(InviteRefused(name=task.name, reason="already a member"))

    async def reject_with_a_non_event(self, task: SendInvite) -> None:
        self.attempts += 1
        raise TaskRejectedError(Untyped())

    async def note_refusal(self, event: InviteRefused) -> None:
        self.refusals.append(event)

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
    await migrate_event_log(database)
    async with database.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE tasks.queue, tasks.parked, events.log, events.subscriptions,"
                " events.parked RESTART IDENTITY"
            )
        )
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

        async def failed_once() -> bool:
            # The failure and its retry time are recorded after the handler returns, so time moves
            # only once they are, or the retry would be due 30 seconds after the moved time.
            return await queue.rows("SELECT attempts FROM tasks.queue") == [(1,)]

        await eventually(failed_once)
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


async def test_a_rejected_task_leaves_the_queue_and_publishes_its_event(queue: Queue) -> None:
    queue.start([TaskHandler(SendInvite, queue.handled.reject_invite)])
    token = request_id.set("req-9")
    try:
        await queue.enqueue(SendInvite(name="Avi"))
    finally:
        request_id.reset(token)

    async def queue_is_empty() -> bool:
        return await queue.rows("SELECT id FROM tasks.queue") == []

    await eventually(queue_is_empty)
    assert queue.handled.attempts == 1, "never retried"
    assert await queue.rows("SELECT id FROM tasks.parked") == [], "not parked"
    assert await queue.rows(
        "SELECT type, payload->>'name', payload->>'reason', request_id FROM events.log"
    ) == [("tests.InviteRefused", "Avi", "already a member", "req-9")]


async def test_a_listener_receives_the_event_of_a_rejected_task(queue: Queue) -> None:
    await queue.enqueue(SendInvite(name="Avi"))
    bus = asyncio.create_task(
        PostgresEventBus(queue.database, queue.time, queue.time.wait).run(
            [Subscription("tests.invites_refused", InviteRefused, queue.handled.note_refusal)],
            queue.stop,
        )
    )
    queue.consumers.append(bus)

    async def subscribed() -> bool:
        return len(await queue.rows("SELECT name FROM events.subscriptions")) == 1

    await eventually(subscribed)
    queue.start([TaskHandler(SendInvite, queue.handled.reject_invite)])

    await eventually(lambda: len(queue.handled.refusals) == 1)
    assert queue.handled.refusals == [InviteRefused(name="Avi", reason="already a member")]


async def test_a_rejected_task_stays_queued_when_its_event_cannot_be_published(
    queue: Queue,
) -> None:
    async with queue.database.begin() as connection:
        await connection.execute(
            text(
                "CREATE OR REPLACE FUNCTION events.refuse_events() RETURNS trigger"
                " LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'the event log is down'; END $$"
            )
        )
        await connection.execute(
            text(
                "CREATE TRIGGER refuse_events BEFORE INSERT ON events.log"
                " FOR EACH STATEMENT EXECUTE FUNCTION events.refuse_events()"
            )
        )
    crashing = queue.start([TaskHandler(SendInvite, queue.handled.reject_invite)])
    queue.consumers.remove(crashing)

    await queue.enqueue(SendInvite(name="Avi"))

    with pytest.RaisesGroup(pytest.RaisesExc(DBAPIError, match="the event log is down")):
        await asyncio.wait_for(crashing, timeout=10)
    assert queue.handled.attempts == 1
    assert await queue.rows("SELECT payload->>'name', attempts FROM tasks.queue") == [("Avi", 0)]
    assert await queue.rows("SELECT id FROM events.log") == []

    async with queue.database.begin() as connection:
        await connection.execute(text("DROP TRIGGER refuse_events ON events.log"))
    queue.start([TaskHandler(SendInvite, queue.handled.reject_invite)])

    async def rejected() -> bool:
        return await queue.rows("SELECT payload->>'name' FROM events.log") == [("Avi",)]

    await eventually(rejected)
    assert queue.handled.attempts == 2
    assert await queue.rows("SELECT id FROM tasks.queue") == []


async def test_retries_a_rejection_whose_event_is_not_a_domain_event(
    queue: Queue, caplog: pytest.LogCaptureFixture
) -> None:
    queue.start([TaskHandler(SendInvite, queue.handled.reject_with_a_non_event)])

    with caplog.at_level(logging.WARNING):
        await queue.enqueue(SendInvite(name="Avi"))

        async def failed_once() -> bool:
            return await queue.rows("SELECT attempts FROM tasks.queue") == [(1,)]

        await eventually(failed_once)

    assert "Untyped has no event_type" in caplog.text
    assert await queue.rows("SELECT id FROM tasks.parked") == []
    assert await queue.rows("SELECT id FROM events.log") == []


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
