"""Domain events: facts a module publishes, which other modules' listeners react to.

A domain event is a frozen Pydantic model with a class-level `event_type`, a stable name such as
`clients.ClientCreated`. Publishing writes it to the event log in the same transaction as the
change it describes. Each subscription reads the log on its own, with its own cursor, so a slow
or failing listener never delays another.

`PostgresEventBus` delivers from the log in Postgres. Another bus, such as a hosted broker,
would implement the same `EventBus` interface, so listeners never change.
"""

import asyncio
import logging
from collections.abc import Callable, Coroutine, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from alembic import command
from alembic.config import Config
from pydantic import BaseModel
from sqlalchemy import Connection, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from libs.infra.cron.cron import Wait, wait_or_stop
from libs.infra.logs.json_logs import request_id
from libs.infra.retry.retry import Exponential, NonRetryableError, RetryStrategy

logger = logging.getLogger(__name__)

MIGRATIONS = Path(__file__).parent / "migrations"
CHANNEL = "domain_events"
# How a subscription retries a failing handler unless it chooses its own strategy.
DEFAULT_RETRY = Exponential()
# When no notification arrives, a subscription still checks the log this often.
POLL_SECONDS = 30.0


def event_type_of(event_class: type[BaseModel]) -> str:
    event_type = getattr(event_class, "event_type", None)
    if not isinstance(event_type, str):
        raise TypeError(f"{event_class.__name__} has no event_type, so it is not a domain event")
    return event_type


@dataclass(frozen=True)
class Subscription[E: BaseModel]:
    """Calls `handle` with every event of `event` published after the subscription first ran.

    `name` keeps the subscription's place in the log, so it must stay the same across releases.
    `retry` decides how a failing handler is retried before its event is parked; a handler that
    raises NonRetryableError has its event parked at once.
    """

    name: str
    event: type[E]
    handle: Callable[[E], Coroutine[Any, Any, None]]
    retry: RetryStrategy = DEFAULT_RETRY

    def __post_init__(self) -> None:
        event_type_of(self.event)


class EventBus(Protocol):
    async def run(self, subscriptions: Sequence[Subscription[Any]], stop: asyncio.Event) -> None:
        """Delivers events to the subscriptions until `stop` is set."""
        ...


async def append_events(connection: AsyncConnection, events: Sequence[BaseModel]) -> None:
    """Writes the events to the log within the caller's transaction. Listeners learn about them
    when the transaction commits; when it rolls back, the events never happened."""
    if not events:
        return
    await connection.execute(
        text(
            "INSERT INTO events.log (type, payload, request_id)"
            " VALUES (:type, CAST(:payload AS jsonb), :request_id)"
        ),
        [
            {
                "type": event_type_of(type(event)),
                "payload": event.model_dump_json(),
                "request_id": request_id.get(),
            }
            for event in events
        ],
    )
    await connection.execute(text("SELECT pg_notify(:channel, '')"), {"channel": CHANNEL})


async def migrate_event_log(database: AsyncEngine) -> None:
    async with database.begin() as connection:
        await connection.run_sync(_upgrade)


def _upgrade(connection: Connection) -> None:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    config.attributes["connection"] = connection
    command.upgrade(config, "head")


class PostgresEventBus:
    """Delivers events from the log in Postgres, at least once, in the order they were published.

    A handler that fails is retried as its subscription's retry strategy says. When the strategy
    stops, or the handler raises NonRetryableError, the event is parked in `events.parked` and
    the subscription moves on. Only one copy of a deployable delivers each subscription at a time.
    """

    def __init__(
        self, database: AsyncEngine, now: Callable[[], datetime], wait: Wait = wait_or_stop
    ) -> None:
        self._database = database
        self._now = now
        self._wait = wait

    async def run(self, subscriptions: Sequence[Subscription[Any]], stop: asyncio.Event) -> None:
        await self._register(subscriptions)
        news = [asyncio.Event() for _ in subscriptions]

        def on_notify(*_: object) -> None:
            for new_events in news:
                new_events.set()

        async with self._database.connect() as listening:
            driver = (await listening.get_raw_connection()).driver_connection
            assert driver is not None, "an open connection always has its driver connection"
            await driver.add_listener(CHANNEL, on_notify)
            try:
                async with asyncio.TaskGroup() as tasks:
                    for subscription, new_events in zip(subscriptions, news, strict=True):
                        tasks.create_task(
                            self._deliver_until_stopped(subscription, new_events, stop)
                        )
            finally:
                await driver.remove_listener(CHANNEL, on_notify)

    async def _register(self, subscriptions: Sequence[Subscription[Any]]) -> None:
        """Adds each new subscription with its cursor at the end of the log."""
        async with self._database.begin() as connection:
            for subscription in subscriptions:
                await connection.execute(
                    text(
                        "INSERT INTO events.subscriptions (name, last_event_id)"
                        " SELECT :name, coalesce(max(id), 0) FROM events.log"
                        " ON CONFLICT (name) DO NOTHING"
                    ),
                    {"name": subscription.name},
                )

    async def _deliver_until_stopped(
        self, subscription: Subscription[Any], new_events: asyncio.Event, stop: asyncio.Event
    ) -> None:
        while not stop.is_set():
            new_events.clear()  # Cleared before reading, so a notification during it is kept.
            wait_seconds = await self._deliver_next(subscription)
            if wait_seconds > 0:
                await self._wait_for_news(new_events, wait_seconds, stop)

    async def _wait_for_news(
        self, new_events: asyncio.Event, seconds: float, stop: asyncio.Event
    ) -> None:
        tasks = {
            asyncio.create_task(new_events.wait()),
            asyncio.create_task(self._wait(seconds, stop)),
        }
        try:
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in tasks:
                task.cancel()

    async def _deliver_next(self, subscription: Subscription[Any]) -> float:
        """Delivers the subscription's next event. Returns 0 when it delivered or parked one, or
        how long to wait: until a retry is due, or until new events may have arrived."""
        async with self._database.begin() as connection:
            state = (
                await connection.execute(
                    text(
                        "SELECT last_event_id, failed_event_id, attempts, retry_at"
                        " FROM events.subscriptions WHERE name = :name FOR UPDATE SKIP LOCKED"
                    ),
                    {"name": subscription.name},
                )
            ).one_or_none()
            if state is None:
                return POLL_SECONDS  # Another copy of the deployable is delivering it.
            event = (
                await connection.execute(
                    text(
                        "SELECT id, payload::text, request_id FROM events.log"
                        " WHERE id > :after AND type = :type ORDER BY id LIMIT 1"
                    ),
                    {"after": state.last_event_id, "type": event_type_of(subscription.event)},
                )
            ).one_or_none()
            if event is None:
                return POLL_SECONDS
            if state.failed_event_id == event.id and state.retry_at > self._now():
                return (state.retry_at - self._now()).total_seconds()
            token = request_id.set(event.request_id or f"event-{subscription.name}-{event.id}")
            try:
                await subscription.handle(subscription.event.model_validate_json(event.payload))
            except Exception as error:
                attempts = (state.attempts if state.failed_event_id == event.id else 0) + 1
                delay = (
                    None
                    if isinstance(error, NonRetryableError)
                    else subscription.retry.delay_after(attempts)
                )
                await self._record_failure(
                    connection, subscription, event.id, attempts, delay, error
                )
                return delay or 0
            finally:
                request_id.reset(token)
            await self._advance(connection, subscription, event.id)
            return 0

    async def _record_failure(
        self,
        connection: AsyncConnection,
        subscription: Subscription[Any],
        event_id: int,
        attempts: int,
        delay: float | None,
        error: Exception,
    ) -> None:
        if delay is not None:
            logger.warning(
                "event %d failed for subscription %s, attempt %d",
                event_id,
                subscription.name,
                attempts,
                exc_info=error,
            )
            await connection.execute(
                text(
                    "UPDATE events.subscriptions SET failed_event_id = :event_id,"
                    " attempts = :attempts, retry_at = :retry_at WHERE name = :name"
                ),
                {
                    "name": subscription.name,
                    "event_id": event_id,
                    "attempts": attempts,
                    "retry_at": self._now() + timedelta(seconds=delay),
                },
            )
            return
        logger.error(
            "event %d parked for subscription %s after %d attempts",
            event_id,
            subscription.name,
            attempts,
            exc_info=error,
        )
        await connection.execute(
            text(
                "INSERT INTO events.parked (subscription, event_id, error)"
                " VALUES (:name, :event_id, :error)"
            ),
            {"name": subscription.name, "event_id": event_id, "error": repr(error)},
        )
        await self._advance(connection, subscription, event_id)

    async def _advance(
        self, connection: AsyncConnection, subscription: Subscription[Any], event_id: int
    ) -> None:
        await connection.execute(
            text(
                "UPDATE events.subscriptions SET last_event_id = :event_id,"
                " failed_event_id = NULL, attempts = 0, retry_at = NULL WHERE name = :name"
            ),
            {"name": subscription.name, "event_id": event_id},
        )
