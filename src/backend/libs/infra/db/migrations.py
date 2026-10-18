"""Applies a folder of Alembic migrations to the database."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import AsyncEngine


async def apply_migrations(database: AsyncEngine, folder: Path) -> None:
    """Upgrades the database to the newest migration in `folder`, in one transaction. The
    folder's env.py reads the connection from the config's `attributes`."""
    async with database.begin() as connection:
        await connection.run_sync(_upgrade, folder)


def _upgrade(connection: Connection, folder: Path) -> None:
    config = Config()
    config.set_main_option("script_location", str(folder))
    config.attributes["connection"] = connection
    command.upgrade(config, "head")
