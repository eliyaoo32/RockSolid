"""Calls the backend the way the frontend does: through the generated clients, with a sign-in
token, for E2E tests driven through the API."""

from protobuf.wkt import FieldMask

from e2e.framework.system import System
from users.v1.users_connect import UsersServiceClientSync
from users.v1.users_pb import GetCurrentUserRequest, UpdateUserRequest, User

USERS_SERVICE = "/users.v1.UsersService"


def current_user(system: System, token: str) -> User | None:
    """The user the backend signs in with `token`. Raises `ConnectError` when it refuses."""
    with _users(system) as users:
        response = users.get_current_user(GetCurrentUserRequest(), headers=_signed_in(token))
    return response.user


def change_display_name(system: System, token: str, display_name: str) -> User | None:
    """Changes the display name of the user `token` signs in, and returns the changed user.
    Raises `ConnectError` when the backend refuses."""
    signed_in = current_user(system, token)
    assert signed_in is not None
    request = UpdateUserRequest(
        user=User(name=signed_in.name, display_name=display_name),
        update_mask=FieldMask(paths=["display_name"]),
    )
    with _users(system) as users:
        response = users.update_user(request, headers=_signed_in(token))
    return response.user


def _users(system: System) -> UsersServiceClientSync:
    deployable = system.serving(USERS_SERVICE)
    assert deployable is not None, f"No deployable serves {USERS_SERVICE}"
    return UsersServiceClientSync(deployable.url)


def _signed_in(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}
