"""Drives the conversations API through its ConnectRPC contract, as a signed-in user's chat
screen would, after the user talked to the agents over AG-UI."""

from collections.abc import Awaitable, Sequence
from datetime import timedelta

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from protobuf.wkt import FieldMask

from conversations.v1.conversations_connect import ConversationsServiceClient
from conversations.v1.conversations_pb import (
    Conversation,
    GetConversationRequest,
    ListConversationsRequest,
    Message,
    UpdateConversationRequest,
)
from libs.testing.agents import AgentClient
from libs.testing.time import FakeTime

ASSISTANT = "assistant"


def name_of(thread: str, agent: str = ASSISTANT) -> str:
    return f"agents/{agent}/conversations/{thread}"


class ConversationsDriver:
    def __init__(
        self, api: ConversationsServiceClient, agents: AgentClient, time: FakeTime
    ) -> None:
        self.when = _When(self, api, agents, time)
        self.get = _Get(self, api)
        self.token: str | None = None
        self.error: Code | None = None
        self.next_page_token = ""
        self.changed: Conversation | None = None

    def headers(self) -> dict[str, str]:
        return {} if self.token is None else {"authorization": f"Bearer {self.token}"}

    async def call[T](self, call: Awaitable[T]) -> T | None:
        """Awaits the call, keeping its error code in `error` and returning None when it fails."""
        self.error = None
        try:
            return await call
        except ConnectError as error:
            self.error = error.code
            return None


class _When:
    def __init__(
        self,
        driver: ConversationsDriver,
        api: ConversationsServiceClient,
        agents: AgentClient,
        time: FakeTime,
    ) -> None:
        self._driver = driver
        self._api = api
        self._agents = agents
        self._time = time

    def sign_in_as(self, user_id: str) -> None:
        self._driver.token = f"token-{user_id}"

    def sign_in_with_a_bad_token(self) -> None:
        self._driver.token = "forged"

    def sign_out(self) -> None:
        self._driver.token = None

    def wait(self, minutes: int) -> None:
        self._time.advance(timedelta(minutes=minutes))

    async def say(self, thread: str, text: str, *, to: str = ASSISTANT) -> None:
        """The signed-in user sends `text` in their thread with the agent, which answers it."""
        reply = await self._agents.send(to, thread, text, token=self._driver.token)
        assert reply.status == 200 and reply.error is None, reply

    async def rename(self, name: str, title: str) -> None:
        await self.update(name, title=title, paths=["title"])

    async def pin(self, name: str, pinned: bool = True) -> None:
        await self.update(name, pinned=pinned, paths=["pinned"])

    async def update(
        self, name: str, *, title: str = "", pinned: bool = False, paths: Sequence[str]
    ) -> None:
        """Updates the conversation with `paths` as the mask. `get.changed()` then holds the
        answer, or `get.error()` the error code."""
        request = UpdateConversationRequest(
            conversation=Conversation(name=name, title=title, pinned=pinned),
            update_mask=FieldMask(paths=list(paths)),
        )
        response = await self._driver.call(
            self._api.update_conversation(request, headers=self._driver.headers())
        )
        self._driver.changed = None if response is None else response.conversation


class _Get:
    def __init__(self, driver: ConversationsDriver, api: ConversationsServiceClient) -> None:
        self._driver = driver
        self._api = api

    async def conversations(
        self, parent: str = f"agents/{ASSISTANT}", *, page_size: int = 0, page_token: str = ""
    ) -> list[Conversation] | None:
        """One page of the signed-in user's conversations, or None when the call fails. The
        page's token is then in `next_page_token()`."""
        request = ListConversationsRequest(
            parent=parent, page_size=page_size, page_token=page_token
        )
        response = await self._driver.call(
            self._api.list_conversations(request, headers=self._driver.headers())
        )
        if response is None:
            return None
        self._driver.next_page_token = response.next_page_token
        return list(response.conversations)

    async def titles(self, parent: str = f"agents/{ASSISTANT}") -> list[str]:
        """The titles of the first page of conversations, in their order, each pinned one marked
        `pinned: `."""
        conversations = await self.conversations(parent)
        assert conversations is not None, self._driver.error
        return [("pinned: " if c.pinned else "") + c.title for c in conversations]

    async def conversation(self, name: str) -> tuple[Conversation, list[Message]] | None:
        """The conversation and its messages, or None when the call fails."""
        response = await self._driver.call(
            self._api.get_conversation(
                GetConversationRequest(name=name), headers=self._driver.headers()
            )
        )
        if response is None:
            return None
        assert response.conversation is not None
        return response.conversation, list(response.messages)

    def next_page_token(self) -> str:
        return self._driver.next_page_token

    def changed(self) -> Conversation | None:
        return self._driver.changed

    def error(self) -> Code | None:
        return self._driver.error
