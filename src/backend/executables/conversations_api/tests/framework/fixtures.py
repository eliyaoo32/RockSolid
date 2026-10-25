"""Runs the conversations API beside two agents, with fake sign-in and an echoing model, through
the runtime on a real Postgres."""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text

from conversations.v1.conversations_connect import ConversationsServiceClient
from executables.conversations_api.conversations_api import ConversationsApiExecutable
from executables.conversations_api.tests.framework.agents import Assistant, Helper, echoing_model
from executables.conversations_api.tests.framework.driver import ConversationsDriver
from libs.testing.agents import AgentClient
from libs.testing.models import FakeModels
from libs.testing.runtime import run_executables
from libs.testing.users import fake_auth


@pytest.fixture
async def driver(database_url: str) -> AsyncIterator[ConversationsDriver]:
    async with run_executables(
        [ConversationsApiExecutable, Assistant, Helper],
        database_url,
        auth=fake_auth(),
        models=FakeModels(echoing_model()),
    ) as running:
        async with running.database.begin() as connection:
            await connection.execute(text("TRUNCATE conversations.conversations"))
        async with ConversationsServiceClient(f"http://127.0.0.1:{running.port}") as api:
            yield ConversationsDriver(api, AgentClient(running.port), running.time)
