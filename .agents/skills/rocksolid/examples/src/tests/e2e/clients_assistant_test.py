from uuid import uuid4

import pytest
from connectrpc.code import Code
from connectrpc.errors import ConnectError

from conversations.v1.conversations_pb import MessageRole
from e2e.framework.agents import talk_to_agent
from e2e.framework.api import change_conversation, conversation, conversations
from e2e.framework.fakes.ollama import ANSWER, API_KEY
from e2e.framework.system import DEBUG_USER_JWT, running_system

ASSISTANT = "clients_assistant"


def test_continues_a_conversation_after_the_backend_restarts(database_url: str) -> None:
    thread = str(uuid4())
    with running_system(database_url) as system:
        first = talk_to_agent(system, ASSISTANT, thread, "Hi, who are my clients?", DEBUG_USER_JWT)
        assert first.status == 200
        assert first.text == ANSWER

        system.restart()
        again = talk_to_agent(system, ASSISTANT, thread, "And who is newest?", DEBUG_USER_JWT)

        assert again.text == ANSWER
        # The backend kept the conversation, so the model hears it from the start.
        assert system.ollama.user_messages() == ["Hi, who are my clients?", "And who is newest?"]


def test_answers_only_the_signed_in_debug_user(database_url: str) -> None:
    thread = str(uuid4())
    with running_system(database_url) as system:
        signed_out = talk_to_agent(system, ASSISTANT, thread, "Hi", token=None)
        forged = talk_to_agent(system, ASSISTANT, thread, "Hi", token="someone-elses-token")
        signed_in = talk_to_agent(system, ASSISTANT, thread, "Hi", DEBUG_USER_JWT)

        assert (signed_out.status, forged.status) == (401, 401)
        assert signed_in.text == ANSWER
        assert len(system.ollama.requests) == 1, "the model heard only the signed-in user"
        authorization, _ = system.ollama.requests[0]
        assert authorization == f"Bearer {API_KEY}", "the backend signs in with its API key"


def test_lists_renames_and_pins_the_users_conversations_across_a_restart(
    database_url: str,
) -> None:
    clients, avi = str(uuid4()), str(uuid4())
    clients_name = f"agents/{ASSISTANT}/conversations/{clients}"
    avi_name = f"agents/{ASSISTANT}/conversations/{avi}"
    with running_system(database_url) as system:
        talk_to_agent(system, ASSISTANT, clients, "Hi, who are my clients?", DEBUG_USER_JWT)
        talk_to_agent(system, ASSISTANT, avi, "Add Avi Cohen", DEBUG_USER_JWT)

        listed = conversations(system, DEBUG_USER_JWT, ASSISTANT)
        assert [(c.name, c.title, c.pinned) for c in listed] == [
            (avi_name, "Add Avi Cohen", False),
            (clients_name, "Hi, who are my clients?", False),
        ]

        change_conversation(
            system,
            DEBUG_USER_JWT,
            clients_name,
            title="My clients",
            pinned=True,
            paths=["title", "pinned"],
        )
        # A blank title is a mistake the backend refuses, and the old title stays.
        with pytest.raises(ConnectError) as refused:
            change_conversation(system, DEBUG_USER_JWT, avi_name, title="   ", paths=["title"])
        assert refused.value.code == Code.INVALID_ARGUMENT

        system.restart()
        listed = conversations(system, DEBUG_USER_JWT, ASSISTANT)
        assert [(c.title, c.pinned) for c in listed] == [
            ("My clients", True),
            ("Add Avi Cohen", False),
        ]

        talk_to_agent(system, ASSISTANT, clients, "And who is newest?", DEBUG_USER_JWT)
        opened = conversation(system, DEBUG_USER_JWT, clients_name)
        assert [(m.role, m.text) for m in opened.messages] == [
            (MessageRole.USER, "Hi, who are my clients?"),
            (MessageRole.ASSISTANT, ANSWER),
            (MessageRole.USER, "And who is newest?"),
            (MessageRole.ASSISTANT, ANSWER),
        ]

        change_conversation(system, DEBUG_USER_JWT, clients_name, pinned=False, paths=["pinned"])
        change_conversation(system, DEBUG_USER_JWT, avi_name, title="Avi", paths=["title"])
        listed = conversations(system, DEBUG_USER_JWT, ASSISTANT)
        assert [(c.title, c.pinned) for c in listed] == [
            ("My clients", False),
            ("Avi", False),
        ], "the conversation with the newest message lists first"
