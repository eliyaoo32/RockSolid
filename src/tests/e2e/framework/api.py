"""Calls the backend the way the frontend does: through the generated clients, with a sign-in
token, for E2E tests driven through the API."""

from collections.abc import Sequence

from protobuf.wkt import FieldMask

from conversations.v1.conversations_connect import ConversationsServiceClientSync
from conversations.v1.conversations_pb import (
    Conversation,
    GetConversationRequest,
    GetConversationResponse,
    ListConversationsRequest,
    UpdateConversationRequest,
)
from e2e.framework.system import System
from users.v1.users_connect import UsersServiceClientSync
from users.v1.users_pb import GetCurrentUserRequest, UpdateUserRequest, User

USERS_SERVICE = "/users.v1.UsersService"
CONVERSATIONS_SERVICE = "/conversations.v1.ConversationsService"


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


def conversations(system: System, token: str | None, agent: str) -> list[Conversation]:
    """The first page of the conversations with `agent` of the user `token` signs in, or of no
    one when it is None. Raises `ConnectError` when the backend refuses."""
    request = ListConversationsRequest(parent=f"agents/{agent}")
    with ConversationsServiceClientSync(_url_of(system, CONVERSATIONS_SERVICE)) as api:
        return list(api.list_conversations(request, headers=_signed_in(token)).conversations)


def conversation(system: System, token: str, name: str) -> GetConversationResponse:
    """The conversation named `name`, with its messages. Raises `ConnectError` when the backend
    refuses."""
    with ConversationsServiceClientSync(_url_of(system, CONVERSATIONS_SERVICE)) as api:
        return api.get_conversation(GetConversationRequest(name=name), headers=_signed_in(token))


def change_conversation(
    system: System,
    token: str,
    name: str,
    *,
    title: str = "",
    pinned: bool = False,
    paths: Sequence[str],
) -> Conversation | None:
    """Changes the fields `paths` names of the conversation named `name`, and returns the changed
    conversation. Raises `ConnectError` when the backend refuses."""
    request = UpdateConversationRequest(
        conversation=Conversation(name=name, title=title, pinned=pinned),
        update_mask=FieldMask(paths=list(paths)),
    )
    with ConversationsServiceClientSync(_url_of(system, CONVERSATIONS_SERVICE)) as api:
        return api.update_conversation(request, headers=_signed_in(token)).conversation


def _users(system: System) -> UsersServiceClientSync:
    return UsersServiceClientSync(_url_of(system, USERS_SERVICE))


def _url_of(system: System, service: str) -> str:
    deployable = system.serving(service)
    assert deployable is not None, f"No deployable serves {service}"
    return deployable.url


def _signed_in(token: str | None) -> dict[str, str]:
    return {} if token is None else {"authorization": f"Bearer {token}"}
