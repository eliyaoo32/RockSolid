"""A conversation between a caller and an agent: every message said, and whether the agent is
answering right now."""

from datetime import datetime, timedelta
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints
from pydantic_ai.messages import ModelMessage, ModelRequest, UserPromptPart

from modules.users.domain.user import UserId

# The agent's run is stopped after this long. So a run that started earlier is over, even when
# its process died without saying so, and the user can send their next message.
MAX_RUN_TIME = timedelta(minutes=10)

AgentName = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,63}$")]


class ConversationBusyError(Exception):
    """The agent is still answering the conversation's previous message."""


class ConversationKey(BaseModel):
    """Identifies a conversation. The same thread under another owner, or with another agent, is
    another conversation, so a caller can neither reach nor detect anyone else's."""

    model_config = ConfigDict(frozen=True)

    agent: AgentName
    # None for an anonymous caller, whose random thread ID is the only key to the conversation.
    owner_id: UserId | None
    thread_id: UUID


class Conversation(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(frozen=True)
    key: ConversationKey = Field(frozen=True)
    # Every message so far, oldest first, as Pydantic AI's own messages (an owner decision).
    messages: list[ModelMessage] = Field(default_factory=list[ModelMessage])
    # When the agent started answering the user's latest message; None when it is not answering.
    run_started_at: AwareDatetime | None = None
    create_time: AwareDatetime = Field(frozen=True)
    update_time: AwareDatetime

    def is_running(self, now: datetime) -> bool:
        """Whether the agent is answering: its run started less than MAX_RUN_TIME ago."""
        return self.run_started_at is not None and now < self.run_started_at + MAX_RUN_TIME

    def append_message(self, message: ModelMessage, now: datetime) -> None:
        """Adds a message. A user's message starts the agent's run, and is refused with
        ConversationBusyError while the agent is answering the previous one."""
        if _from_the_user(message):
            if self.is_running(now):
                raise ConversationBusyError
            self.run_started_at = now
        self.messages.append(message)
        self.update_time = now

    def end_run(self, now: datetime) -> None:
        """The agent stopped answering: it answered, failed, or was stopped. Every message stays,
        so the user can send their next message after an unanswered one."""
        if self.run_started_at is not None:
            self.run_started_at = None
            self.update_time = now


def _from_the_user(message: ModelMessage) -> bool:
    return isinstance(message, ModelRequest) and any(
        isinstance(part, UserPromptPart) for part in message.parts
    )
