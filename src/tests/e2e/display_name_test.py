import pytest
from connectrpc.code import Code
from connectrpc.errors import ConnectError

from e2e.framework.api import change_display_name, current_user
from e2e.framework.system import DEBUG_USER_JWT, DEBUG_USER_NAME, running_system


def test_a_user_changes_their_display_name_and_keeps_it_after_a_restart(
    database_url: str,
) -> None:
    with running_system(database_url) as system:
        user = current_user(system, DEBUG_USER_JWT)
        assert user is not None
        assert user.display_name == DEBUG_USER_NAME

        with pytest.raises(ConnectError) as refused:
            change_display_name(system, DEBUG_USER_JWT, "x" * 101)
        assert refused.value.code == Code.INVALID_ARGUMENT
        user = current_user(system, DEBUG_USER_JWT)
        assert user is not None
        assert user.display_name == DEBUG_USER_NAME

        changed = change_display_name(system, DEBUG_USER_JWT, "Dana")
        assert changed is not None
        assert changed.display_name == "Dana"

        system.restart()
        user = current_user(system, DEBUG_USER_JWT)
        assert user is not None
        assert user.display_name == "Dana"
