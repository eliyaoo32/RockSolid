"""Starts the backend: migrates each module's schema, then serves its APIs."""

import asyncio
from datetime import UTC, datetime

import uvicorn
from sqlalchemy.ext.asyncio import create_async_engine

from deployables.backend.config import Settings
from executables.clients_api import clients_api
from modules.users.services.setup import create_auth


def now() -> datetime:
    return datetime.now(UTC)


async def serve() -> None:
    # Settings reads its required fields from the environment, which Pyright cannot see.
    settings = Settings()  # pyright: ignore[reportCallIssue]
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    auth = create_auth(settings.firebase_project_id)
    await clients_api.migrate(engine)
    app = clients_api.create_app(engine, auth, now)
    try:
        await uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=settings.port)).serve()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(serve())
