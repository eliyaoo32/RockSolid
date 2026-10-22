"""Runs the clients assistant through the runtime, on a real Postgres, with fake sign-in and a
scripted model in place of Ollama."""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text

from executables.clients_assistant.clients_assistant import ClientsAssistantExecutable
from executables.clients_assistant.tests.framework.driver import AssistantDriver
from executables.clients_assistant.tests.framework.model import scripted_model
from libs.testing.agents import AgentClient
from libs.testing.models import FakeModels
from libs.testing.runtime import run_executables
from libs.testing.users import fake_auth
from modules.clients.services.setup import create_client_service


@pytest.fixture
def models() -> FakeModels:
    return FakeModels(scripted_model())


@pytest.fixture
async def driver(database_url: str, models: FakeModels) -> AsyncIterator[AssistantDriver]:
    async with run_executables(
        [ClientsAssistantExecutable], database_url, auth=fake_auth(), models=models
    ) as running:
        async with running.database.begin() as connection:
            await connection.execute(text("TRUNCATE clients.clients, conversations.conversations"))
        clients = create_client_service(running.database, running.time)
        yield AssistantDriver(AgentClient(running.port), clients)
