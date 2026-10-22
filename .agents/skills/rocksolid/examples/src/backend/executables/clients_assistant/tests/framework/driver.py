"""Drives the clients assistant: users talk to it over AG-UI, and the driver reads its answers
and the clients each user then has."""

from libs.testing.agents import AgentClient, AgentReply
from modules.clients.services.clients import MAX_PAGE_SIZE, ClientService

THREAD = "00000000-0000-4000-8000-0000000000aa"


class AssistantDriver:
    def __init__(self, agent: AgentClient, clients: ClientService) -> None:
        self.when = _When(agent)
        self.get = _Get(self.when, clients)


class _When:
    def __init__(self, agent: AgentClient) -> None:
        self._agent = agent
        self.replies: list[AgentReply] = []

    async def user_says(self, user_id: str | None, text: str) -> AgentReply:
        """`user_id` sends `text` in their thread with the assistant; None sends it signed out."""
        token = None if user_id is None else f"token-{user_id}"
        reply = await self._agent.send("clients_assistant", THREAD, text, token=token)
        self.replies.append(reply)
        return reply


class _Get:
    def __init__(self, when: _When, clients: ClientService) -> None:
        self._when = when
        self._clients = clients

    def answer(self) -> str:
        """The text of the assistant's latest answer."""
        return self._when.replies[-1].text

    async def clients_of(self, user_id: str) -> list[str]:
        """The names of the user's clients, newest first."""
        page = await self._clients.list(user_id, MAX_PAGE_SIZE, "", "")
        return [client.display_name for client in page.clients]
