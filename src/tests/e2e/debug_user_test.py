import pytest
from connectrpc.code import Code
from connectrpc.errors import ConnectError

from e2e.framework.api import current_user
from e2e.framework.system import DEBUG_USER_JWT, DEBUG_USER_NAME, running_system


@pytest.mark.parametrize("debug", [None, "false", "0", "no"])
def test_refuses_the_debug_user_token_unless_the_backend_runs_with_debug_true(
    database_url: str, debug: str | None
) -> None:
    # The token is not a Firebase ID token either, so Firebase's check refuses it without
    # asking Google.
    with (
        running_system(database_url, debug=debug) as system,
        pytest.raises(ConnectError) as refused,
    ):
        current_user(system, DEBUG_USER_JWT)

    assert refused.value.code == Code.UNAUTHENTICATED


def test_signs_in_the_debug_user_on_a_backend_run_with_debug_true(database_url: str) -> None:
    with running_system(database_url, debug="true") as system:
        user = current_user(system, DEBUG_USER_JWT)

    assert user is not None
    assert user.display_name == DEBUG_USER_NAME
    assert user.email == "debug-user@example.com"
