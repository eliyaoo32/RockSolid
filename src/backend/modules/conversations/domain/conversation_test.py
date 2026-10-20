from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from pydantic import ValidationError

from modules.conversations.domain.conversation import (
    RUN_LEASE,
    ActiveRun,
    Conversation,
    ConversationBusyError,
    ConversationKey,
    RunNotActiveError,
)

NOW = datetime(2026, 10, 17, 9, 0, tzinfo=UTC)
FIRST_RUN = UUID("00000000-0000-4000-8000-000000000001")
SECOND_RUN = UUID("00000000-0000-4000-8000-000000000002")
THREAD = UUID("00000000-0000-4000-8000-0000000000aa")
KEY = ConversationKey(agent="clients_assistant", owner_id="uid-dana", thread_id=THREAD)


def new_conversation() -> Conversation:
    return Conversation(
        id=UUID("00000000-0000-4000-8000-0000000000bb"), key=KEY, create_time=NOW, update_time=NOW
    )


def test_starts_empty_and_answering_nothing() -> None:
    conversation = new_conversation()

    assert conversation.history == "[]"
    assert conversation.active_run is None
    assert not conversation.is_answering(NOW)


def test_answers_one_message_at_a_time() -> None:
    conversation = new_conversation()

    conversation.start_run(FIRST_RUN, NOW)

    assert conversation.active_run == ActiveRun(run_id=FIRST_RUN, started_at=NOW)
    assert conversation.is_answering(NOW + RUN_LEASE - timedelta(seconds=1))
    with pytest.raises(ConversationBusyError):
        conversation.start_run(SECOND_RUN, NOW + timedelta(minutes=1))


def test_finishing_a_run_keeps_its_history_and_frees_the_conversation() -> None:
    conversation = new_conversation()
    conversation.start_run(FIRST_RUN, NOW)

    conversation.finish_run(FIRST_RUN, '[{"kind": "request"}]', NOW + timedelta(seconds=5))

    assert conversation.history == '[{"kind": "request"}]'
    assert conversation.active_run is None
    assert conversation.update_time == NOW + timedelta(seconds=5)
    conversation.start_run(SECOND_RUN, NOW + timedelta(seconds=6))
    assert conversation.active_run == ActiveRun(
        run_id=SECOND_RUN, started_at=NOW + timedelta(seconds=6)
    )


def test_abandoning_a_run_keeps_the_history_and_frees_the_conversation() -> None:
    conversation = new_conversation()
    conversation.start_run(FIRST_RUN, NOW)
    conversation.finish_run(FIRST_RUN, '["before"]', NOW)
    conversation.start_run(SECOND_RUN, NOW)

    assert conversation.abandon_run(SECOND_RUN, NOW + timedelta(seconds=3))

    assert conversation.history == '["before"]'
    assert conversation.active_run is None
    assert not conversation.abandon_run(SECOND_RUN, NOW), "a run is abandoned only once"


def test_a_run_that_outlives_its_lease_is_taken_over() -> None:
    conversation = new_conversation()
    conversation.start_run(FIRST_RUN, NOW)

    assert not conversation.is_answering(NOW + RUN_LEASE)
    conversation.start_run(SECOND_RUN, NOW + RUN_LEASE)

    assert conversation.active_run == ActiveRun(run_id=SECOND_RUN, started_at=NOW + RUN_LEASE)
    with pytest.raises(RunNotActiveError):
        conversation.finish_run(FIRST_RUN, '["late"]', NOW + RUN_LEASE)
    assert not conversation.abandon_run(FIRST_RUN, NOW + RUN_LEASE), "the new run stays"
    assert conversation.history == "[]"


def test_a_run_that_never_started_cannot_finish() -> None:
    conversation = new_conversation()

    with pytest.raises(RunNotActiveError):
        conversation.finish_run(FIRST_RUN, '["answer"]', NOW)


def test_an_anonymous_conversation_has_no_owner() -> None:
    key = ConversationKey(agent="clients_assistant", owner_id=None, thread_id=THREAD)

    assert key != KEY, "the same thread with and without an owner is two conversations"


@pytest.mark.parametrize("agent", ["", "Clients", "clients-assistant", "1clients", "a" * 65])
def test_an_agent_name_is_lowercase_words_joined_by_underscores(agent: str) -> None:
    with pytest.raises(ValidationError):
        ConversationKey(agent=agent, owner_id=None, thread_id=THREAD)
