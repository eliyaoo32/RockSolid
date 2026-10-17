import asyncio
import logging
from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

import pytest
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from libs.infra.events.events import (
    PostgresEventBus,
    Subscription,
    append_events,
    migrate_event_log,
)
from libs.infra.logs.json_logs import request_id
from libs.testing.time import FakeTime, eventually

START = datetime(2026, 10, 17, 9, 0, tzinfo=UTC)


class Greeted(BaseModel):
    model_config = ConfigDict(frozen=True)
    event_type: ClassVar[str] = "tests.Greeted"
    name: str


class Waved(BaseModel):
    model_config = ConfigDict(frozen=True)
    event_type: ClassVar[str] = "tests.Waved"
    hand: str


class Untyped(BaseModel):
    """Has no event_type, so it is not a domain event."""


class Handled:
    """Records what each subscription handled, and fails on the names it is told to fail on."""

    def __init__(self) -> None:
        self.greetings: list[str] = []
        self.second_greetings: list[str] = []
        self.waves: list[str] = []
        self.request_ids: list[str | None] = []
        self.failing: set[str] = set()
        self.attempts = 0

    async def greet(self, event: Greeted) -> None:
        self.attempts += 1
        if event.name in self.failing:
            raise RuntimeError(f"cannot greet {event.name}")
        self.greetings.append(event.name)
        self.request_ids.append(request_id.get())

    async def greet_again(self, event: Greeted) -> None:
        self.second_greetings.append(event.name)

    async def wave(self, event: Waved) -> None:
        self.waves.append(event.hand)


class Bus:
    def __init__(self, database: AsyncEngine) -> None:
        self.database = database
        self.time = FakeTime(START)
        self.handled = Handled()
        self.stop = asyncio.Event()
        self.tasks: list[asyncio.Task[None]] = []

    def subscriptions(self) -> Sequence[Subscription[Any]]:
        return [
            Subscription("greet", Greeted, self.handled.greet),
            Subscription("greet_again", Greeted, self.handled.greet_again),
            Subscription("wave", Waved, self.handled.wave),
        ]

    async def publish(self, *events: BaseModel) -> None:
        async with self.database.begin() as connection:
            await append_events(connection, events)

    async def rows(self, query: str) -> list[tuple[object, ...]]:
        async with self.database.connect() as connection:
            return [tuple(row) for row in await connection.execute(text(query))]


@pytest.fixture
async def bus(database_url: str) -> AsyncIterator[Bus]:
    database = create_async_engine(database_url)
    await migrate_event_log(database)
    async with database.begin() as connection:
        await connection.execute(
            text("TRUNCATE events.log, events.subscriptions, events.parked RESTART IDENTITY")
        )
    bus = Bus(database)
    yield bus
    bus.stop.set()
    for task in bus.tasks:
        await task
    await database.dispose()


async def registered(bus: Bus, count: int) -> None:
    async def all_registered() -> bool:
        return len(await bus.rows("SELECT name FROM events.subscriptions")) >= count

    await eventually(all_registered)


async def started(bus: Bus, subscriptions: Sequence[Subscription[Any]] | None = None) -> None:
    bus.tasks.append(
        asyncio.create_task(
            PostgresEventBus(bus.database, bus.time, bus.time.wait).run(
                subscriptions or bus.subscriptions(), bus.stop
            )
        )
    )
    await registered(bus, len(subscriptions or bus.subscriptions()))


async def test_delivers_each_event_in_order_to_every_subscription_of_its_type(bus: Bus) -> None:
    await started(bus)

    await bus.publish(Greeted(name="Avi"), Waved(hand="left"), Greeted(name="Noa"))

    await eventually(lambda: len(bus.handled.greetings) == 2 and len(bus.handled.waves) == 1)
    await eventually(lambda: len(bus.handled.second_greetings) == 2)
    assert bus.handled.greetings == ["Avi", "Noa"]
    assert bus.handled.second_greetings == ["Avi", "Noa"]
    assert bus.handled.waves == ["left"]


async def test_a_new_subscription_starts_after_the_events_already_published(bus: Bus) -> None:
    await bus.publish(Greeted(name="before"))
    await started(bus)

    await bus.publish(Greeted(name="after"))

    await eventually(lambda: bus.handled.greetings == ["after"])


async def test_retries_a_failing_handler_with_backoff_until_it_succeeds(bus: Bus) -> None:
    await started(bus)
    bus.handled.failing.add("Avi")

    await bus.publish(Greeted(name="Avi"), Greeted(name="Noa"))
    await eventually(lambda: bus.handled.attempts == 1)

    bus.time.advance(timedelta(seconds=1))
    await bus.publish(Greeted(name="Dana"))  # Wakes the subscription before its retry is due.
    await asyncio.sleep(0.05)
    assert bus.handled.attempts == 1, "no retry before the backoff ends"

    bus.time.advance(timedelta(seconds=1))
    await eventually(lambda: bus.handled.attempts == 2)
    bus.handled.failing.clear()
    bus.time.advance(timedelta(seconds=4))

    await eventually(lambda: bus.handled.greetings == ["Avi", "Noa", "Dana"])


async def test_parks_an_event_that_keeps_failing_and_moves_on(
    bus: Bus, caplog: pytest.LogCaptureFixture
) -> None:
    await started(bus)
    bus.handled.failing.add("Avi")

    with caplog.at_level(logging.WARNING):
        await bus.publish(Greeted(name="Avi"), Greeted(name="Noa"))
        for attempt in range(1, 6):
            await eventually(lambda attempt=attempt: bus.handled.attempts >= attempt)
            bus.time.advance(timedelta(minutes=10))

        await eventually(lambda: bus.handled.greetings == ["Noa"])

    parked = await bus.rows("SELECT subscription, event_id, error FROM events.parked")
    assert len(parked) == 1
    assert parked[0][:2] == ("greet", 1)
    assert "cannot greet Avi" in str(parked[0][2])
    assert "event 1 parked for subscription greet" in caplog.text


async def test_parks_an_event_whose_payload_no_longer_fits_its_class(bus: Bus) -> None:
    await started(bus)
    async with bus.database.begin() as connection:
        await connection.execute(
            text("INSERT INTO events.log (type, payload) VALUES ('tests.Greeted', '{\"nam\": 1}')")
        )
        await connection.execute(text("SELECT pg_notify('domain_events', '')"))

    for attempt in range(1, 5):

        async def failed(attempt: int = attempt) -> bool:
            rows = await bus.rows("SELECT attempts FROM events.subscriptions WHERE name = 'greet'")
            return rows == [(attempt,)]

        await eventually(failed)
        bus.time.advance(timedelta(minutes=10))
    await bus.publish(Greeted(name="Noa"))

    await eventually(lambda: bus.handled.greetings == ["Noa"])
    assert (
        len(await bus.rows("SELECT event_id FROM events.parked WHERE subscription = 'greet'")) == 1
    )


async def test_hands_each_event_to_one_worker_when_a_deployable_runs_twice(bus: Bus) -> None:
    subscriptions = [Subscription("greet", Greeted, bus.handled.greet)]
    await started(bus, subscriptions)
    await started(bus, subscriptions)

    await bus.publish(*(Greeted(name=f"guest {n}") for n in range(20)))

    await eventually(lambda: len(bus.handled.greetings) == 20)
    await asyncio.sleep(0.1)
    assert sorted(bus.handled.greetings) == sorted(f"guest {n}" for n in range(20))


async def test_handles_an_event_under_the_request_id_that_published_it(bus: Bus) -> None:
    await started(bus)
    token = request_id.set("req-77")
    try:
        await bus.publish(Greeted(name="Avi"))
    finally:
        request_id.reset(token)

    await eventually(lambda: bus.handled.request_ids == ["req-77"])


def test_rejects_a_model_without_an_event_type() -> None:
    async def handle(event: Untyped) -> None: ...

    with pytest.raises(TypeError, match="Untyped has no event_type"):
        Subscription("untyped", Untyped, handle)


async def test_refuses_to_publish_a_model_without_an_event_type(bus: Bus) -> None:
    with pytest.raises(TypeError, match="Untyped has no event_type"):
        await bus.publish(Untyped())


async def test_publishing_no_events_writes_nothing(bus: Bus) -> None:
    await bus.publish()

    assert await bus.rows("SELECT id FROM events.log") == []
