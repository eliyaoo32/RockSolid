"""Tasks: commands a module queues, which exactly one handler runs.

A task is a frozen Pydantic model with a class-level `task_type`, a stable name such as
`clients.SendClientWelcome`. Queuing writes it in the same transaction as the change that asks
for it. Each task type has one handler, in one executable of one deployable, which runs it once
it succeeds. A handler that refuses a task raises TaskRejectedError with a domain event, which
the queue publishes as it removes the task.

`PostgresTaskQueue` runs tasks from the queue in Postgres. Another queue, such as a hosted
broker, would implement the same `TaskQueue` interface, so consumers never change.
"""

import asyncio
import logging
from collections.abc import Callable, Coroutine, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from libs.infra.cron.cron import Wait, wait_until
from libs.infra.db.migrations import apply_migrations
from libs.infra.db.notifications import run_on_notifications
from libs.infra.events.events import append_events, event_type_of
from libs.infra.logs.json_logs import request_id
from libs.infra.retry.retry import Exponential, NonRetryableError, RetryStrategy

logger = logging.getLogger(__name__)

MIGRATIONS = Path(__file__).parent / "migrations"
CHANNEL = "tasks"
# How a handler's failing tasks are retried unless it chooses its own strategy.
DEFAULT_RETRY = Exponential()
# When no notification arrives, a handler still checks the queue this often.
POLL = timedelta(seconds=30)


def task_type_of(task_class: type[BaseModel]) -> str:
    task_type = getattr(task_class, "task_type", None)
    if not isinstance(task_type, str):
        raise TypeError(f"{task_class.__name__} has no task_type, so it is not a task")
    return task_type


class TaskRejectedError(Exception):
    """A handler raises it to refuse its task for a reason the module that queued the task
    handles. The queue removes the task and publishes `event` in one transaction."""

    def __init__(self, event: BaseModel) -> None:
        super().__init__(f"task rejected with {event_type_of(type(event))}")
        self.event = event


@dataclass(frozen=True)
class TaskHandler[T: BaseModel]:
    """Calls `handle` with every queued task of `task`.

    `retry` decides how a failing task is retried before it is parked; a handler that raises
    NonRetryableError has its task parked at once.
    """

    task: type[T]
    handle: Callable[[T], Coroutine[Any, Any, None]]
    retry: RetryStrategy = DEFAULT_RETRY

    def __post_init__(self) -> None:
        task_type_of(self.task)


class TaskQueue(Protocol):
    async def run(self, handlers: Sequence[TaskHandler[Any]], stop: asyncio.Event) -> None:
        """Runs the queued tasks of the handlers' types until `stop` is set."""
        ...


async def enqueue_tasks(connection: AsyncConnection, tasks: Sequence[BaseModel]) -> None:
    """Queues the tasks within the caller's transaction. Handlers see them when the transaction
    commits; when it rolls back, they were never queued."""
    if not tasks:
        return
    await connection.execute(
        text(
            "INSERT INTO tasks.queue (type, payload, request_id)"
            " VALUES (:type, CAST(:payload AS jsonb), :request_id)"
        ),
        [
            {
                "type": task_type_of(type(task)),
                "payload": task.model_dump_json(),
                "request_id": request_id.get(),
            }
            for task in tasks
        ],
    )
    await connection.execute(text("SELECT pg_notify(:channel, '')"), {"channel": CHANNEL})


async def migrate_task_queue(database: AsyncEngine) -> None:
    await apply_migrations(database, MIGRATIONS)


class PostgresTaskQueue:
    """Runs tasks from the queue in Postgres, at least once each, oldest first.

    A task stays locked in its transaction while its handler runs, so when the process crashes,
    the task returns to the queue. A handler that fails is retried as its retry strategy says.
    When the strategy stops, or the handler raises NonRetryableError, the task moves to
    `tasks.parked`. A handler that raises TaskRejectedError has its task removed and its event
    appended to the event log in the same transaction.

    shortcut: each process runs one task of each type at a time, and holds a transaction open
    while it runs; run several workers per handler, or claim tasks without holding the
    transaction, when a task type needs more throughput or runs for minutes.
    """

    def __init__(
        self, database: AsyncEngine, now: Callable[[], datetime], wait: Wait | None = None
    ) -> None:
        self._database = database
        self._now = now
        self._wait = wait or partial(wait_until, now)

    async def run(self, handlers: Sequence[TaskHandler[Any]], stop: asyncio.Event) -> None:
        workers = [partial(self._run_next, handler) for handler in handlers]
        await run_on_notifications(self._database, CHANNEL, workers, self._wait, stop)

    async def _run_next(self, handler: TaskHandler[Any]) -> datetime | None:
        """Runs the handler's next due task. Returns None when it ran or failed one, or when to
        look again: when a retry is due, or when new tasks may have arrived."""
        task_type = task_type_of(handler.task)
        async with self._database.begin() as connection:
            task = (
                await connection.execute(
                    text(
                        "SELECT id, payload::text, request_id, attempts FROM tasks.queue"
                        " WHERE type = :type AND (retry_at IS NULL OR retry_at <= :now)"
                        " ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED"
                    ),
                    {"type": task_type, "now": self._now()},
                )
            ).one_or_none()
            if task is None:
                return await self._next_look(connection, task_type)
            token = request_id.set(task.request_id or f"task-{task_type}-{task.id}")
            try:
                await handler.handle(handler.task.model_validate_json(task.payload))
            except TaskRejectedError as rejection:
                await append_events(connection, [rejection.event])
            except Exception as error:
                attempts = task.attempts + 1
                delay = (
                    None
                    if isinstance(error, NonRetryableError)
                    else handler.retry.delay_after(attempts)
                )
                await self._record_failure(connection, task_type, task.id, attempts, delay, error)
                return None
            finally:
                request_id.reset(token)
            await connection.execute(
                text("DELETE FROM tasks.queue WHERE id = :id"), {"id": task.id}
            )
            return None

    async def _next_look(self, connection: AsyncConnection, task_type: str) -> datetime:
        """When the type's next retry is due, or when new tasks may have arrived, whichever
        comes first."""
        next_retry = (
            await connection.execute(
                text(
                    "SELECT min(retry_at) FROM tasks.queue WHERE type = :type AND retry_at > :now"
                ),
                {"type": task_type, "now": self._now()},
            )
        ).scalar()
        poll = self._now() + POLL
        return poll if next_retry is None else min(next_retry, poll)

    async def _record_failure(
        self,
        connection: AsyncConnection,
        task_type: str,
        task_id: int,
        attempts: int,
        delay: float | None,
        error: Exception,
    ) -> None:
        if delay is not None:
            logger.warning(
                "task %d of type %s failed, attempt %d",
                task_id,
                task_type,
                attempts,
                exc_info=error,
            )
            await connection.execute(
                text(
                    "UPDATE tasks.queue SET attempts = :attempts, retry_at = :retry_at"
                    " WHERE id = :id"
                ),
                {
                    "id": task_id,
                    "attempts": attempts,
                    "retry_at": self._now() + timedelta(seconds=delay),
                },
            )
            return
        logger.error(
            "task %d of type %s parked after %d attempts",
            task_id,
            task_type,
            attempts,
            exc_info=error,
        )
        await connection.execute(
            text(
                "WITH parked AS (DELETE FROM tasks.queue WHERE id = :id"
                " RETURNING id, type, payload, request_id)"
                " INSERT INTO tasks.parked (id, type, payload, request_id, attempts, error)"
                " SELECT id, type, payload, request_id, :attempts, :error FROM parked"
            ),
            {"id": task_id, "attempts": attempts, "error": repr(error)},
        )
