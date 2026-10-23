"""Builds the clients module and migrates its schema, for the executables that host it."""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from pydantic import HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from modules.clients.repositories.mail_api_clients import MailApiWelcomeMailer
from modules.clients.repositories.postgres_clients import PostgresClientRepository
from modules.clients.services.clients import ClientService

MIGRATIONS = Path(__file__).parent.parent / "migrations"


class ClientsSettings(BaseSettings):
    """The clients module's settings, from the environment variables that start with `CLIENTS_`.
    Each has a value that loads anywhere, so every executable that hosts the module starts."""

    model_config = SettingsConfigDict(env_prefix="CLIENTS_")

    # Where the mail API, which sends clients their email, answers.
    mail_api_url: HttpUrl = HttpUrl("https://mail-api.example.com")
    # A secret: production sets it, and without it no email is sent.
    mail_api_key: SecretStr | None = None


def create_client_service(database: AsyncEngine, now: Callable[[], datetime]) -> ClientService:
    settings = ClientsSettings()
    mailer = MailApiWelcomeMailer(str(settings.mail_api_url), settings.mail_api_key)
    return ClientService(PostgresClientRepository(database), mailer, now)


async def migrate_schema(database: AsyncEngine) -> None:
    async with database.begin() as connection:
        await connection.run_sync(_upgrade)


def _upgrade(connection: Connection) -> None:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    config.attributes["connection"] = connection
    command.upgrade(config, "head")
