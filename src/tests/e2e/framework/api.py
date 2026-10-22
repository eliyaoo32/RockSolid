"""Calls the backend the way the frontend does: through the generated clients, with a sign-in
token, for E2E tests driven through the API."""

from e2e.framework.system import System
from users.v1.users_connect import UsersServiceClientSync
from users.v1.users_pb import GetCurrentUserRequest, User

USERS_SERVICE = "/users.v1.UsersService"


def current_user(system: System, token: str) -> User | None:
    """The user the backend signs in with `token`. Raises `ConnectError` when it refuses."""
    deployable = system.serving(USERS_SERVICE)
    assert deployable is not None, f"No deployable serves {USERS_SERVICE}"
    with UsersServiceClientSync(deployable.url) as users:
        response = users.get_current_user(
            GetCurrentUserRequest(), headers={"authorization": f"Bearer {token}"}
        )
    return response.user
