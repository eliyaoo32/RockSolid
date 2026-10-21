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
    ConversationBusyError,
    ConversationKey,
)

NOW = datetime(2026, 10, 17, 9, 0, tzinfo=UTC)
THREAD = UUID("00000000-0000-4000-8000-0000000000aa")
KEY = ConversationKey(agent="clients_assistant", owner_id="uid-dana", thread_id=THREAD)


def users(text: str) -> ModelRequest:
    return ModelRequest(parts=[UserPromptPart(text, timestamp=NOW)])


def agents(text: str) -> ModelResponse:
    return ModelResponse(parts=[TextPart(text)])


def new_conversation() -> Conversation:
    return Conversation(
        id=UUID("00000000-0000-4000-8000-0000000000bb"), key=KEY, create_time=NOW, update_time=NOW
    )


def test_starts_with_no_messages_and_the_agent_not_running() -> None:
    conversation = new_conversation()

    assert conversation.messages == []
    assert not conversation.is_running(NOW)


def test_a_users_message_starts_the_agents_run_until_it_ends() -> None:
    conversation = new_conversation()

    conversation.append_message(users("Who are my clients?"), NOW)
    assert conversation.is_running(NOW + MAX_RUN_TIME - timedelta(seconds=1))

    call = ToolCallPart("list_clients", {}, tool_call_id="call-1")
    conversation.append_message(ModelResponse(parts=[call]), NOW + timedelta(seconds=1))
    conversation.append_message(
        ModelRequest(parts=[ToolReturnPart("list_clients", [], tool_call_id="call-1")]),
        NOW + timedelta(seconds=2),
    )
    conversation.append_message(agents("You have none yet."), NOW + timedelta(seconds=3))
    conversation.end_run(NOW + timedelta(seconds=3))

    assert not conversation.is_running(NOW + timedelta(seconds=3))
    assert len(conversation.messages) == 4, "the agent's tool call and its result are kept too"
    assert conversation.update_time == NOW + timedelta(seconds=3)


def test_refuses_the_users_next_message_while_the_agent_is_answering() -> None:
    conversation = new_conversation()
    conversation.append_message(users("first"), NOW)

    with pytest.raises(ConversationBusyError):
        conversation.append_message(users("second"), NOW + timedelta(minutes=1))

    assert conversation.messages == [users("first")]


def test_a_stopped_run_keeps_the_users_message_and_takes_the_next_one() -> None:
    conversation = new_conversation()
    conversation.append_message(users("never answered"), NOW)

    conversation.end_run(NOW + timedelta(seconds=5))
    conversation.append_message(users("on top"), NOW + timedelta(seconds=6))

    assert conversation.messages == [users("never answered"), users("on top")]
    assert conversation.is_running(NOW + timedelta(seconds=6))


def test_takes_the_users_next_message_once_a_run_outlives_its_time() -> None:
    conversation = new_conversation()
    # A process that died mid-answer never ends its run.
    conversation.append_message(users("never answered"), NOW)

    assert not conversation.is_running(NOW + MAX_RUN_TIME)
    conversation.append_message(users("on top"), NOW + MAX_RUN_TIME)

    assert conversation.messages == [users("never answered"), users("on top")]
    assert conversation.run_started_at == NOW + MAX_RUN_TIME


def test_ending_a_run_that_is_not_running_changes_nothing() -> None:
    conversation = new_conversation()

    conversation.end_run(NOW + timedelta(seconds=5))

    assert conversation.update_time == NOW


def test_an_anonymous_conversation_has_no_owner() -> None:
    key = ConversationKey(agent="clients_assistant", owner_id=None, thread_id=THREAD)

    assert key != KEY, "the same thread with and without an owner is two conversations"


@pytest.mark.parametrize("agent", ["", "Clients", "clients-assistant", "1clients", "a" * 65])
def test_an_agent_name_is_lowercase_words_joined_by_underscores(agent: str) -> None:
    with pytest.raises(ValidationError):
        ConversationKey(agent=agent, owner_id=None, thread_id=THREAD)
