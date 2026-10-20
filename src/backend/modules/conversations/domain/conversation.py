"""A conversation between a caller and an agent, which answers one message at a time."""

from datetime import datetime, timedelta
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints

from modules.users.domain.user import UserId

# A run still answering after this long is taken for dead, such as when its process crashed,
# and the next message may take the conversation over.
RUN_LEASE = timedelta(minutes=10)

AgentName = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,63}$")]


class ConversationBusyError(Exception):
    """The conversation is answering another message."""


class RunNotActiveError(Exception):
    """The run is not the conversation's active run: it already ended, or another run took the
    conversation over after the run's lease expired."""


class ConversationKey(BaseModel):
    """Identifies a conversation. The same thread under another owner, or with another agent, is
    another conversation, so a caller can neither reach nor detect anyone else's."""

    model_config = ConfigDict(frozen=True)

    agent: AgentName
    # None for an anonymous caller, whose random thread ID is the only key to the conversation.
    owner_id: UserId | None
    thread_id: UUID


class ActiveRun(BaseModel):
    """The run answering the conversation's latest message."""

    model_config = ConfigDict(frozen=True)

    run_id: UUID
    started_at: AwareDatetime


class Conversation(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(frozen=True)
    key: ConversationKey = Field(frozen=True)
    # The messages so far, as JSON in the agent runtime's format.
    history: str = "[]"
    active_run: ActiveRun | None = None
    create_time: AwareDatetime = Field(frozen=True)
    update_time: AwareDatetime

    def is_answering(self, now: datetime) -> bool:
        """Whether a run is answering a message and its lease has not expired."""
        return self.active_run is not None and now < self.active_run.started_at + RUN_LEASE

    def start_run(self, run_id: UUID, now: datetime) -> None:
        """Starts answering a message. Raises ConversationBusyError while another run answers."""
        if self.is_answering(now):
            raise ConversationBusyError
        self.active_run = ActiveRun(run_id=run_id, started_at=now)
        self.update_time = now

    def finish_run(self, run_id: UUID, history: str, now: datetime) -> None:
        """Keeps the history the run ended with. Raises RunNotActiveError when the run is not the
        active one, so a run taken over never overwrites the run that took over."""
        if self.active_run is None or self.active_run.run_id != run_id:
            raise RunNotActiveError
        self.history = history
        self.active_run = None
        self.update_time = now

    def abandon_run(self, run_id: UUID, now: datetime) -> bool:
        """Ends the run without changing the history. Returns False when the run is not the
        active one, which leaves the conversation as it is."""
        if self.active_run is None or self.active_run.run_id != run_id:
            return False
        self.active_run = None
        self.update_time = now
        return True
