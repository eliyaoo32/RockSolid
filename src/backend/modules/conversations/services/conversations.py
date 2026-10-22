"""The conversations use cases: adding the user's message, adding the agent's answer, and
stopping a run that ended without one."""

from collections.abc import Callable, Sequence
from datetime import datetime
from uuid import uuid4

from pydantic_ai.messages import ModelMessage

from modules.conversations.domain.conversation import Conversation, ConversationKey
from modules.conversations.repositories.conversation_repository import ConversationRepository


class ConversationService:
    def __init__(self, repository: ConversationRepository, now: Callable[[], datetime]) -> None:
        self._repository = repository
        self._now = now

    async def receive_message(
        self, key: ConversationKey, message: ModelMessage
    ) -> list[ModelMessage]:
        """Adds the user's message, creating the conversation on its first one, and returns every
        message for the agent to answer. Raises ConversationBusyError while the agent is still
        answering the previous message."""
        now = self._now()

        def receive(conversation: Conversation) -> list[ModelMessage]:
            conversation.append_message(message, now)
            return list(conversation.messages)

        return await self._repository.change(key, self._new(key, now), receive)

    async def append_messages(self, key: ConversationKey, messages: Sequence[ModelMessage]) -> None:
        """Adds what the agent's run produced: its tool calls, their results, and its answer."""
        now = self._now()

        def append(conversation: Conversation) -> None:
            for message in messages:
                conversation.append_message(message, now)

        await self._repository.change(key, self._new(key, now), append)

    async def stop(self, key: ConversationKey) -> bool:
        """Stops the agent's run if it ended without an answer, such as when it failed or the
        user stopped it. Returns False when there was nothing to stop."""
        now = self._now()
        return await self._repository.change(key, self._new(key, now), lambda c: c.stop(now))

    def _new(self, key: ConversationKey, now: datetime) -> Conversation:
        """The conversation to add when the key has none yet."""
        return Conversation(id=uuid4(), key=key, create_time=now, update_time=now)
