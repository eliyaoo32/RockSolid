from collections.abc import Callable
from datetime import datetime
from typing import Protocol
from uuid import UUID

from modules.conversations.domain.conversation import AgentName, Conversation, ConversationKey
from modules.users.domain.user import UserId


class ConversationRepository(Protocol):
    """Loads and saves conversations by their key."""

    async def change[T](
        self,
        key: ConversationKey,
        new: Conversation | None,
        change: Callable[[Conversation], T],
    ) -> T:
        """Loads the conversation with this key, or adds `new` when there is none, applies
        `change` to it, and saves it, all in one transaction that holds the conversation until it
        ends, so changes to one conversation happen one after another. Returns what `change`
        returns; when `change` raises, nothing is saved. Raises ConversationNotFoundError when
        there is none and `new` is None."""
        ...

    async def get(self, key: ConversationKey) -> Conversation | None:
        """Returns the conversation with this key, or None when there is none."""
        ...

    async def list_pinned_first(
        self,
        agent: AgentName,
        owner_id: UserId,
        limit: int,
        after: tuple[bool, datetime, UUID] | None,
    ) -> list[Conversation]:
        """Returns up to `limit` of the owner's conversations with the agent that have a message,
        ordered by (pinned, last_message_time, id), all descending, starting after the given
        (pinned, last_message_time, id)."""
        ...
