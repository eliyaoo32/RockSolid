"""Calls the backend the way the frontend does: through the generated clients, with a sign-in
token, for E2E tests driven through the API."""

from e2e.framework.system import Backend
from users.v1.users_connect import UsersServiceClientSync
from users.v1.users_pb import GetCurrentUserRequest, User


def current_user(backend: Backend, token: str) -> User | None:
    """The user the backend signs in with `token`. Raises `ConnectError` when it refuses."""
    with UsersServiceClientSync(backend.url) as users:
        response = users.get_current_user(
            GetCurrentUserRequest(), headers={"authorization": f"Bearer {token}"}
        )
    return response.user
