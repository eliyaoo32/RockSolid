import pytest
from connectrpc.code import Code
from connectrpc.errors import ConnectError

from e2e.framework.api import change_conversation, conversation, conversations
from e2e.framework.system import DEBUG_USER_JWT, running_system

# The framework runs no agent, so the debug user has no conversations; a project's agent tests
# list, open, rename, and pin real ones.
UNKNOWN = "agents/assistant/conversations/0f8fad5b-d9cb-469f-a165-70867728950e"


def test_serves_the_signed_in_users_conversations_only(database_url: str) -> None:
    with running_system(database_url) as system:
        with pytest.raises(ConnectError) as refused:
            conversations(system, None, "assistant")
        assert refused.value.code == Code.UNAUTHENTICATED

        assert conversations(system, DEBUG_USER_JWT, "assistant") == []
        for open_or_rename in [
            lambda: conversation(system, DEBUG_USER_JWT, UNKNOWN),
            lambda: change_conversation(
                system, DEBUG_USER_JWT, UNKNOWN, title="x", paths=["title"]
            ),
        ]:
            with pytest.raises(ConnectError) as missing:
                open_or_rename()
            assert missing.value.code == Code.NOT_FOUND
