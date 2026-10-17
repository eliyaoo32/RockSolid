"""Builds the clients module and migrates its schema, for the executables that host it."""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from modules.clients.repositories.postgres_clients import PostgresClientRepository
from modules.clients.services.clients import ClientService

MIGRATIONS = Path(__file__).parent.parent / "migrations"


def create_client_service(database: AsyncEngine, now: Callable[[], datetime]) -> ClientService:
    return ClientService(PostgresClientRepository(database), now)


async def migrate_schema(database: AsyncEngine) -> None:
    async with database.begin() as connection:
        await connection.run_sync(_upgrade)


def _upgrade(connection: Connection) -> None:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    config.attributes["connection"] = connection
    command.upgrade(config, "head")
