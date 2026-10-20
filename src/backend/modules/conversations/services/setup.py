"""Builds the conversations module and migrates its schema, for the agent runtime."""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from modules.conversations.repositories.postgres_conversations import PostgresConversationRepository
from modules.conversations.services.conversations import ConversationService

MIGRATIONS = Path(__file__).parent.parent / "migrations"


def create_conversation_service(
    database: AsyncEngine, now: Callable[[], datetime]
) -> ConversationService:
    return ConversationService(PostgresConversationRepository(database), now)


async def migrate_schema(database: AsyncEngine) -> None:
    async with database.begin() as connection:
        await connection.run_sync(_upgrade)


def _upgrade(connection: Connection) -> None:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    config.attributes["connection"] = connection
    command.upgrade(config, "head")
