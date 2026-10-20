"""Helps a signed-in user look up and add their clients, in a conversation."""

from pydantic import ValidationError
from pydantic_ai import Agent, ModelRetry, RunContext, Tool

from libs.infra.filtering.filtering import InvalidFilterError
from libs.infra.runtime.agents import AgentDeps
from libs.infra.runtime.executables import AgentExecutable
from modules.clients.domain.client import Client
from modules.clients.services.clients import MAX_PAGE_SIZE
from modules.clients.services.setup import create_client_service, migrate_schema

MODEL = "deepseek-v4.1-flash:cloud"
INSTRUCTIONS = (
    "You help the user look up and add their clients. Use the tools for every fact about a"
    " client, and never make one up. When a tool says a value is invalid, fix it or ask the user."
)


class ClientsAssistantExecutable(AgentExecutable):
    name = "clients_assistant"
    require_auth = True
    migrations = (migrate_schema,)

    def agent(self) -> Agent[AgentDeps, str]:
        clients = create_client_service(self.infra.database, self.infra.now)

        async def list_clients(ctx: RunContext[AgentDeps], filter: str = "") -> list[Client]:
            """Lists the user's clients, newest first, up to 100.

            Args:
                filter: An OData filter on display_name, email, create_time, or update_time,
                    such as `contains(display_name, 'Avi')`. Empty lists every client.
            """
            try:
                page = await clients.list(ctx.deps.signed_in_user_id(), MAX_PAGE_SIZE, "", filter)
            except InvalidFilterError as error:
                fields = ", ".join(error.valid_paths)
                raise ModelRetry(f"filter: {error}. Filterable fields: {fields}.") from error
            return page.clients

        async def create_client(
            ctx: RunContext[AgentDeps], display_name: str, email: str | None = None
        ) -> Client:
            """Adds a client for the user.

            Args:
                display_name: The client's name, as the user calls them.
                email: The client's email address, when the user gave one.
            """
            try:
                return await clients.create(ctx.deps.signed_in_user_id(), display_name, email)
            except ValidationError as error:
                raise ModelRetry(f"The client is not valid: {error}") from error

        return Agent(
            self.infra.models.ollama(MODEL),
            deps_type=AgentDeps,
            instructions=INSTRUCTIONS,
            tools=[Tool(list_clients), Tool(create_client)],
        )
