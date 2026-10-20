from collections.abc import Callable
from typing import Protocol

from modules.conversations.domain.conversation import Conversation, ConversationKey


class ConversationRepository(Protocol):
    """Loads and saves conversations by their key."""

    async def change[T](
        self,
        key: ConversationKey,
        new: Conversation,
        change: Callable[[Conversation], T],
    ) -> T:
        """Loads the conversation with this key, or adds `new` when there is none, applies
        `change` to it, and saves it, all in one transaction that holds the conversation until it
        ends, so changes to one conversation happen one after another. Returns what `change`
        returns; when `change` raises, nothing is saved."""
        ...
