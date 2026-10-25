from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from pydantic import ValidationError
from pydantic_ai.messages import (
    ImageUrl,
    ModelRequest,
    ModelResponse,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from modules.conversations.domain.conversation import (
    MAX_RUN_TIME,
    Conversation,
    ConversationKey,
    MessageRole,
    TextMessage,
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


def test_starts_untitled_unpinned_and_with_no_last_message() -> None:
    conversation = new_conversation()

    assert conversation.title is None
    assert not conversation.pinned
    assert conversation.last_message_time is None


def test_is_titled_after_the_users_first_message_and_keeps_that_title() -> None:
    conversation = new_conversation()

    conversation.append_message(users("  Who are\n my   clients?  "), NOW)
    conversation.append_message(agents_answer("You have none yet."), LATER)
    conversation.append_message(users("And who is newest?"), LATER)

    assert conversation.title == "Who are my clients?"


def test_a_long_first_message_is_cut_to_the_longest_title() -> None:
    conversation = new_conversation()

    conversation.append_message(users("word " * 40), NOW)

    assert conversation.title == " ".join(["word"] * 20) + "…"
    assert len(conversation.title or "") == 100


def test_a_first_message_of_exactly_the_longest_title_is_kept_whole() -> None:
    conversation = new_conversation()

    conversation.append_message(users("x" * 100), NOW)

    assert conversation.title == "x" * 100


def test_a_first_message_without_text_leaves_it_untitled_until_one_with_text() -> None:
    conversation = new_conversation()
    image = ImageUrl("https://example.com/plan.png")

    conversation.append_message(ModelRequest(parts=[UserPromptPart([image])]), NOW)
    assert conversation.title is None

    conversation.stop(LATER)
    conversation.append_message(ModelRequest(parts=[UserPromptPart([image, "The plan"])]), LATER)
    assert conversation.title == "The plan"


def test_the_last_message_time_is_when_the_newest_message_was_added() -> None:
    conversation = new_conversation()

    conversation.append_message(users("first"), NOW)
    assert conversation.last_message_time == NOW

    conversation.append_message(agents_answer("Hi"), LATER)
    assert conversation.last_message_time == LATER

    conversation.stop(LATER + timedelta(seconds=1))
    assert conversation.last_message_time == LATER, "stopping adds no message"


def test_a_renamed_title_loses_its_outer_spaces() -> None:
    conversation = new_conversation()
    conversation.append_message(users("first"), NOW)

    conversation.title = "  Dana's clients  "

    assert conversation.title == "Dana's clients"


@pytest.mark.parametrize("title", ["", "   ", "x" * 101])
def test_refuses_a_blank_or_too_long_title_and_keeps_the_old_one(title: str) -> None:
    conversation = new_conversation()
    conversation.append_message(users("first"), NOW)

    with pytest.raises(ValidationError):
        conversation.title = title

    assert conversation.title == "first"


def test_shows_the_users_and_the_agents_text_with_their_times_and_no_tool_calls() -> None:
    conversation = new_conversation()
    conversation.append_message(users("Who are my clients?"), NOW)
    conversation.append_message(agents_tool_call(), LATER)
    conversation.append_message(tool_result(), LATER)
    answer = ModelResponse(
        parts=[ThinkingPart("They have none."), TextPart("You have "), TextPart("none yet.")],
        timestamp=LATER,
    )
    conversation.append_message(answer, LATER)

    assert conversation.text_messages() == [
        TextMessage(role=MessageRole.USER, text="Who are my clients?", send_time=NOW),
        TextMessage(role=MessageRole.ASSISTANT, text="You have none yet.", send_time=LATER),
    ]
