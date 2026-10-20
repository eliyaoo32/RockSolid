"""The conversations use cases: answering one message at a time, and keeping what was said."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from modules.conversations.domain.conversation import Conversation, ConversationKey
from modules.conversations.repositories.conversation_repository import ConversationRepository


@dataclass(frozen=True)
class StartedRun:
    run_id: UUID
    # The messages before this run, as the agent runtime stored them.
    history: str


class ConversationService:
    def __init__(self, repository: ConversationRepository, now: Callable[[], datetime]) -> None:
        self._repository = repository
        self._now = now

    async def start_run(self, key: ConversationKey) -> StartedRun:
        """Starts answering a message in the conversation, creating it on its first message.
        Raises ConversationBusyError while another run answers it."""
        now = self._now()
        run_id = uuid4()

        def start(conversation: Conversation) -> StartedRun:
            conversation.start_run(run_id, now)
            return StartedRun(run_id, conversation.history)

        return await self._repository.change(key, self._new(key, now), start)

    async def finish_run(self, key: ConversationKey, run_id: UUID, history: str) -> None:
        """Keeps the history the run ended with. Raises RunNotActiveError when another run took
        the conversation over, which then keeps its own history."""
        now = self._now()
        await self._repository.change(
            key, self._new(key, now), lambda c: c.finish_run(run_id, history, now)
        )

    async def abandon_run(self, key: ConversationKey, run_id: UUID) -> bool:
        """Ends a run that did not finish, keeping the history as it was before it. Returns
        False when the run had already ended or been taken over."""
        now = self._now()
        return await self._repository.change(
            key, self._new(key, now), lambda c: c.abandon_run(run_id, now)
        )

    def _new(self, key: ConversationKey, now: datetime) -> Conversation:
        """The conversation to add when the key has none yet."""
        return Conversation(id=uuid4(), key=key, create_time=now, update_time=now)
