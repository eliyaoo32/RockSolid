"""A conversation between a caller and an agent: every message said, whether the agent is
answering right now, and how the caller's list of conversations shows it."""

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    UserPromptPart,
)

from modules.users.domain.user import UserId

# The agent's run is stopped after this long. So a run that started earlier is over, even when
# its process died without saying so, and the user can send their next message.
MAX_RUN_TIME = timedelta(minutes=10)

TITLE_MAX_LENGTH = 100

AgentName = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,63}$")]
Title = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=TITLE_MAX_LENGTH)
]


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class TextMessage(BaseModel):
    """One text message, as a chat screen shows it."""

    model_config = ConfigDict(frozen=True)

    role: MessageRole
    text: str
    send_time: AwareDatetime


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
    # When the agent started answering the user's latest message; None once it was stopped.
    run_started_at: AwareDatetime | None = None
    # The user's first text, cut to TITLE_MAX_LENGTH, until they rename it; None until then.
    title: Title | None = None
    pinned: bool = False
    # When the newest message was added; None before the first one.
    last_message_time: AwareDatetime | None = None
    create_time: AwareDatetime = Field(frozen=True)
    update_time: AwareDatetime

    @property
    def is_answered(self) -> bool:
        """Whether the newest message is the agent's full answer, not a call to one of its tools."""
        last = self.messages[-1] if self.messages else None
        return isinstance(last, ModelResponse) and not any(
            isinstance(part, ToolCallPart) for part in last.parts
        )

    def is_timed_out(self, now: datetime) -> bool:
        """Whether the agent's run started MAX_RUN_TIME ago or more, so it is over."""
        return self.run_started_at is not None and now >= self.run_started_at + MAX_RUN_TIME

    def is_running(self, now: datetime) -> bool:
        """Whether the agent is answering: its run started, and it has not answered, been
        stopped, or timed out."""
        return (
            self.run_started_at is not None and not self.is_answered and not self.is_timed_out(now)
        )

    def append_message(self, message: ModelMessage, now: datetime) -> None:
        """Adds a message. A user's message starts the agent's run, and is refused with
        ValueError while the agent is answering the previous one. The agent's full answer ends
        the run. The user's first text titles the conversation."""
        if _from_the_user(message):
            if self.is_running(now):
                raise ValueError("the agent is still answering the previous message")
            self.run_started_at = now
            text = " ".join(_users_text(message).split())
            if self.title is None and text:
                self.title = _cut_to_title(text)
        self.messages.append(message)
        self.last_message_time = now
        self.update_time = now

    def stop(self, now: datetime) -> bool:
        """Stops the agent's run before it answered, such as when it failed or the user stopped
        it. Every message stays, so the user can send their next one on top. Returns False when
        no run was answering."""
        if not self.is_running(now):
            return False
        self.run_started_at = None
        self.update_time = now
        return True

    def text_messages(self) -> list[TextMessage]:
        """The user's and the agent's text, oldest first, each when it was sent. Tool calls,
        their results, and the agent's thinking are left out."""
        texts: list[TextMessage] = []
        for message in self.messages:
            if isinstance(message, ModelResponse):
                text = "".join(p.content for p in message.parts if isinstance(p, TextPart))
                if text:
                    texts.append(
                        TextMessage(
                            role=MessageRole.ASSISTANT, text=text, send_time=message.timestamp
                        )
                    )
            else:
                for part in message.parts:
                    if isinstance(part, UserPromptPart) and (text := _text_of(part)):
                        texts.append(
                            TextMessage(role=MessageRole.USER, text=text, send_time=part.timestamp)
                        )
        return texts


def _from_the_user(message: ModelMessage) -> bool:
    return isinstance(message, ModelRequest) and any(
        isinstance(part, UserPromptPart) for part in message.parts
    )


def _text_of(part: UserPromptPart) -> str:
    """The text the user wrote, without their images or files."""
    if isinstance(part.content, str):
        return part.content
    return "\n".join(item for item in part.content if isinstance(item, str))


def _users_text(message: ModelMessage) -> str:
    return "\n".join(_text_of(p) for p in message.parts if isinstance(p, UserPromptPart))


def _cut_to_title(text: str) -> str:
    if len(text) <= TITLE_MAX_LENGTH:
        return text
    return text[: TITLE_MAX_LENGTH - 1].rstrip() + "…"
