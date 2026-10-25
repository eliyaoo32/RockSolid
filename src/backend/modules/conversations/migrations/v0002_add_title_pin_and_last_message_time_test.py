"""Migrates conversations saved before 0002 and checks what each one gets."""

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from testcontainers.postgres import PostgresContainer

MIGRATIONS = Path(__file__).parent
SAVED = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
ANSWER = {"kind": "response", "parts": [{"part_kind": "text", "content": "Hi"}]}
IMAGE = {"kind": "image-url", "url": "https://example.com/plan.png"}


@pytest.fixture
async def database() -> AsyncIterator[AsyncEngine]:
    with PostgresContainer("postgres:18", driver="asyncpg") as postgres:
        database = create_async_engine(postgres.get_connection_url())
        yield database
        await database.dispose()


async def migrate(database: AsyncEngine, revision: str) -> None:
    def upgrade(connection: Connection) -> None:
        config = Config()
        config.set_main_option("script_location", str(MIGRATIONS))
        config.attributes["connection"] = connection
        command.upgrade(config, revision)

    async with database.begin() as connection:
        await connection.run_sync(upgrade)


def prompt(content: Any) -> dict[str, Any]:
    part = {"part_kind": "user-prompt", "content": content, "timestamp": SAVED.isoformat()}
    return {"kind": "request", "parts": [part]}


async def test_titles_and_times_each_saved_conversation_from_its_messages(
    database: AsyncEngine,
) -> None:
    await migrate(database, "0001")
    saved = {
        "spaces": [prompt("  Who are\n my   clients?  "), ANSWER, prompt("Next")],
        "long": [prompt("word " * 40)],
        "exactly_100": [prompt("x" * 100)],
        "blank_then_text": [prompt("   "), ANSWER, prompt([IMAGE]), prompt("Plan")],
        "only_files": [prompt([IMAGE, "with a caption"])],
        "empty": [],
    }
    async with database.begin() as connection:
        for owner, messages in saved.items():
            await connection.execute(
                text(
                    "INSERT INTO conversations.conversations VALUES (:id, 'assistant', :owner,"
                    " :thread, CAST(:messages AS jsonb), NULL, :saved, :saved)"
                ),
                {
                    "id": uuid4(),
                    "owner": owner,
                    "thread": uuid4(),
                    "messages": json.dumps(messages),
                    "saved": SAVED,
                },
            )

    await migrate(database, "head")

    async with database.connect() as connection:
        rows = await connection.execute(
            text(
                "SELECT key_owner_id, title, pinned, last_message_time"
                " FROM conversations.conversations"
            )
        )
        migrated = {
            row.key_owner_id: (row.title, row.pinned, row.last_message_time) for row in rows
        }
    assert migrated == {
        "spaces": ("Who are my clients?", False, SAVED),
        "long": (" ".join(["word"] * 20) + "…", False, SAVED),
        "exactly_100": ("x" * 100, False, SAVED),
        "blank_then_text": ("Plan", False, SAVED),
        # Plain-text prompts only: the user's next message titles it.
        "only_files": (None, False, SAVED),
        "empty": (None, False, None),
    }
