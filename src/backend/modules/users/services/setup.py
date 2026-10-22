"""Builds the users module's services and migrates its schema, for the deployables that host
them."""

from pathlib import Path

import jwt
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from modules.users.repositories.debug_users import DebugUserRepository
from modules.users.repositories.firebase_users import FIREBASE_SIGNING_KEYS, FirebaseUserRepository
from modules.users.repositories.postgres_users import PostgresUserRepository
from modules.users.services.auth import Auth
from modules.users.services.users import UserService

MIGRATIONS = Path(__file__).parent.parent / "migrations"


def create_auth(
    firebase_project_id: str, debug_user_jwt: str | None = None, debug_user_name: str = "Debug User"
) -> Auth:
    """Signs users in with the Firebase Auth project's ID tokens. Given a debug user's token,
    it signs in only that user, named `debug_user_name`, and Firebase signs in nobody."""
    if debug_user_jwt:
        return Auth(DebugUserRepository(debug_user_jwt, debug_user_name))
    return Auth(FirebaseUserRepository(firebase_project_id, jwt.PyJWKClient(FIREBASE_SIGNING_KEYS)))


def create_user_service(database: AsyncEngine) -> UserService:
    return UserService(PostgresUserRepository(database))


async def migrate_schema(database: AsyncEngine) -> None:
    async with database.begin() as connection:
        await connection.run_sync(_upgrade)


def _upgrade(connection: Connection) -> None:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    config.attributes["connection"] = connection
    command.upgrade(config, "head")
