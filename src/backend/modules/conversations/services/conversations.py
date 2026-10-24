"""The conversations use cases: adding the user's message, adding the agent's answer, stopping
a run that ended without one, and the user listing, reading, renaming, and pinning their
conversations."""

import base64
import binascii
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, TypeAdapter
from pydantic_ai.messages import ModelMessage

from modules.conversations.domain.conversation import AgentName, Conversation, ConversationKey
from modules.conversations.repositories.conversation_repository import ConversationRepository
from modules.conversations.services.errors import (
    ConversationBusyError,
    ConversationNotFoundError,
    InvalidPageError,
)
from modules.users.domain.user import UserId

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100

# Where a page ends: the last conversation's (pinned, last_message_time, id).
_PAGE_POSITION = TypeAdapter(tuple[bool, AwareDatetime, UUID])


class ConversationChanges(BaseModel):
    """The fields to change on a conversation. Only the fields that are set change."""

    title: str = ""
    pinned: bool = False


@dataclass(frozen=True)
class ConversationsPage:
    conversations: list[Conversation]
    next_page_token: str


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
            if conversation.is_running(now):
                raise ConversationBusyError
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

    async def list_conversations(
        self, owner_id: UserId, agent: AgentName, page_size: int, page_token: str
    ) -> ConversationsPage:
        """Returns up to `page_size` of the owner's conversations with the agent, the default
        page size for 0: the pinned ones first, then by their last message, newest first. Raises
        InvalidPageError for a page token this service did not issue."""
        limit = min(page_size or DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE)
        after = _decode_page_token(page_token) if page_token else None
        # One extra conversation tells whether another page exists.
        conversations = await self._repository.list_pinned_first(agent, owner_id, limit + 1, after)
        if len(conversations) <= limit:
            return ConversationsPage(conversations, "")
        last = conversations[limit - 1]
        assert last.last_message_time is not None, "only conversations with a message are listed"
        position = (last.pinned, last.last_message_time, last.id)
        return ConversationsPage(conversations[:limit], _encode_page_token(position))

    async def get(self, key: ConversationKey) -> Conversation:
        """Raises ConversationNotFoundError when the key has no conversation."""
        conversation = await self._repository.get(key)
        if conversation is None:
            raise ConversationNotFoundError
        return conversation

    async def update(self, key: ConversationKey, changes: ConversationChanges) -> Conversation:
        """Renames or pins the conversation. Raises ConversationNotFoundError when the key has no
        conversation, and ValidationError when the title breaks the conversation's rules."""
        now = self._now()

        def update(conversation: Conversation) -> Conversation:
            for field in changes.model_fields_set:
                setattr(conversation, field, getattr(changes, field))
            conversation.update_time = now
            return conversation

        return await self._repository.change(key, None, update)

    def _new(self, key: ConversationKey, now: datetime) -> Conversation:
        """The conversation to add when the key has none yet."""
        return Conversation(id=uuid4(), key=key, create_time=now, update_time=now)


def _encode_page_token(position: tuple[bool, datetime, UUID]) -> str:
    return base64.urlsafe_b64encode(_PAGE_POSITION.dump_json(position)).decode()


def _decode_page_token(token: str) -> tuple[bool, datetime, UUID]:
    try:
        return _PAGE_POSITION.validate_json(base64.urlsafe_b64decode(token))
    except (binascii.Error, ValueError) as error:
        raise InvalidPageError from error
