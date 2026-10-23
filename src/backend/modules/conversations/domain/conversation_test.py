from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from pydantic import ValidationError
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from modules.conversations.domain.conversation import (
    MAX_RUN_TIME,
    Conversation,
    ConversationKey,
)

NOW = datetime(2026, 10, 17, 9, 0, tzinfo=UTC)
LATER = NOW + timedelta(seconds=5)
THREAD = UUID("00000000-0000-4000-8000-0000000000aa")
KEY = ConversationKey(agent="clients_assistant", owner_id="uid-dana", thread_id=THREAD)


def users(text: str) -> ModelRequest:
    return ModelRequest(parts=[UserPromptPart(text, timestamp=NOW)])


def agents_answer(text: str) -> ModelResponse:
    return ModelResponse(parts=[TextPart(text)])


def agents_tool_call() -> ModelResponse:
    return ModelResponse(parts=[ToolCallPart("list_clients", {}, tool_call_id="call-1")])


def tool_result() -> ModelRequest:
    return ModelRequest(parts=[ToolReturnPart("list_clients", [], tool_call_id="call-1")])


def new_conversation() -> Conversation:
    return Conversation(
        id=UUID("00000000-0000-4000-8000-0000000000bb"), key=KEY, create_time=NOW, update_time=NOW
    )


def test_starts_with_no_messages_and_the_agent_not_running() -> None:
    conversation = new_conversation()

    assert conversation.messages == []
    assert not conversation.is_answered
    assert not conversation.is_running(NOW)


def test_the_users_message_starts_the_run_and_the_agents_full_answer_ends_it() -> None:
    conversation = new_conversation()

    conversation.append_message(users("Who are my clients?"), NOW)
    assert conversation.is_running(NOW)

    conversation.append_message(agents_tool_call(), LATER)
    conversation.append_message(tool_result(), LATER)
    assert conversation.is_running(LATER), "a tool call is not the answer"

    conversation.append_message(agents_answer("You have none yet."), LATER)
    assert conversation.is_answered
    assert not conversation.is_running(LATER)
    assert len(conversation.messages) == 4
    assert conversation.update_time == LATER


def test_refuses_the_users_next_message_while_the_agent_is_answering() -> None:
    conversation = new_conversation()
    conversation.append_message(users("first"), NOW)

    with pytest.raises(ValueError, match="still answering"):
        conversation.append_message(users("second"), NOW + timedelta(minutes=1))

    assert conversation.messages == [users("first")]


def test_takes_the_users_next_message_once_the_agent_answered() -> None:
    conversation = new_conversation()
    conversation.append_message(users("first"), NOW)
    conversation.append_message(agents_answer("Hi"), NOW)

    conversation.append_message(users("second"), LATER)

    assert conversation.is_running(LATER)
    assert conversation.run_started_at == LATER


def test_a_stopped_run_keeps_the_users_message_and_takes_the_next_one() -> None:
    conversation = new_conversation()
    conversation.append_message(users("never answered"), NOW)

    assert conversation.stop(LATER)
    conversation.append_message(users("on top"), LATER)

    assert conversation.messages == [users("never answered"), users("on top")]
    assert conversation.is_running(LATER)


def test_takes_the_users_next_message_once_a_run_timed_out() -> None:
    conversation = new_conversation()
    # A process that died mid-answer never stops its run.
    conversation.append_message(users("never answered"), NOW)

    assert conversation.is_timed_out(NOW + MAX_RUN_TIME)
    assert not conversation.is_running(NOW + MAX_RUN_TIME)
    conversation.append_message(users("on top"), NOW + MAX_RUN_TIME)

    assert conversation.messages == [users("never answered"), users("on top")]
    assert not conversation.is_timed_out(NOW + MAX_RUN_TIME), "the new run has its own time"


@pytest.mark.parametrize("answered", [True, False])
def test_stopping_when_no_run_is_answering_changes_nothing(answered: bool) -> None:
    conversation = new_conversation()
    if answered:
        conversation.append_message(users("first"), NOW)
        conversation.append_message(agents_answer("Hi"), NOW)

    assert not conversation.stop(LATER)

    assert conversation.update_time == NOW


def test_an_anonymous_conversation_has_no_owner() -> None:
    key = ConversationKey(agent="clients_assistant", owner_id=None, thread_id=THREAD)

    assert key != KEY, "the same thread with and without an owner is two conversations"


@pytest.mark.parametrize("agent", ["", "Clients", "clients-assistant", "1clients", "a" * 65])
def test_an_agent_name_is_lowercase_words_joined_by_underscores(agent: str) -> None:
    with pytest.raises(ValidationError):
        ConversationKey(agent=agent, owner_id=None, thread_id=THREAD)
