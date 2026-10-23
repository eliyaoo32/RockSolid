from uuid import uuid4

from e2e.framework.agents import talk_to_agent
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
