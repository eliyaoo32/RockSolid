"""Serves the conversations ConnectRPC contract: the signed-in caller's conversations with the
agents, which they list, open, rename, and pin."""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from uuid import UUID

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from connectrpc.request import RequestContext
from protobuf.wkt import Timestamp
from pydantic import ValidationError

from conversations.v1 import conversations_pb as pb
from conversations.v1.conversations_connect import (
    ConversationsService,
    ConversationsServiceASGIApplication,
)
from libs.infra.runtime.executables import RpcApplication, RpcInterceptor, RpcServiceExecutable
from modules.conversations.domain.conversation import (
    Conversation,
    ConversationKey,
    MessageRole,
    TextMessage,
)
from modules.conversations.services.conversations import ConversationChanges, ConversationService
from modules.conversations.services.errors import ConversationNotFoundError, InvalidPageError
from modules.conversations.services.setup import create_conversation_service
from modules.users.domain.user import UserId
from modules.users.services.auth import Auth

AGENTS_PREFIX = "agents/"
ROLES = {MessageRole.USER: pb.MessageRole.USER, MessageRole.ASSISTANT: pb.MessageRole.ASSISTANT}


class ConversationsApiExecutable(RpcServiceExecutable):
    """Serves the conversations contract. The runtime migrates the conversations schema for
    every deployable, so this executable declares no migrations."""

    def application(self, interceptors: Sequence[RpcInterceptor]) -> RpcApplication:
        conversations = create_conversation_service(self.infra.database, self.infra.now)
        return ConversationsServiceASGIApplication(
            ConversationsApi(conversations, self.infra.auth), interceptors=interceptors
        )


class ConversationsApi(ConversationsService):
    def __init__(self, conversations: ConversationService, auth: Auth) -> None:
        self._conversations = conversations
        self._auth = auth

    async def list_conversations(
        self,
        request: pb.ListConversationsRequest,
        ctx: RequestContext[pb.ListConversationsRequest, pb.ListConversationsResponse],
        /,
    ) -> pb.ListConversationsResponse:
        user = self._auth.from_ctx(ctx)
        # An agent that is not one, such as `agents/a/b`, has no conversations.
        agent = request.parent.removeprefix(AGENTS_PREFIX)
        with _connect_errors():
            page = await self._conversations.list_conversations(
                user.id, agent, request.page_size, request.page_token
            )
        return pb.ListConversationsResponse(
            conversations=[_to_message(c) for c in page.conversations],
            next_page_token=page.next_page_token,
        )

    async def get_conversation(
        self,
        request: pb.GetConversationRequest,
        ctx: RequestContext[pb.GetConversationRequest, pb.GetConversationResponse],
        /,
    ) -> pb.GetConversationResponse:
        user = self._auth.from_ctx(ctx)
        with _connect_errors():
            conversation = await self._conversations.get(_key(request.name, user.id))
        return pb.GetConversationResponse(
            conversation=_to_message(conversation),
            messages=[_to_text_message(m) for m in conversation.text_messages()],
        )

    async def update_conversation(
        self,
        request: pb.UpdateConversationRequest,
        ctx: RequestContext[pb.UpdateConversationRequest, pb.UpdateConversationResponse],
        /,
    ) -> pb.UpdateConversationResponse:
        user = self._auth.from_ctx(ctx)
        message = request.conversation or pb.Conversation()
        # The contract checked that the mask names only these fields.
        paths = request.update_mask.paths if request.update_mask else []
        values = {"title": message.title, "pinned": message.pinned}
        changes = ConversationChanges.model_validate({path: values[path] for path in paths})
        with _connect_errors():
            conversation = await self._conversations.update(_key(message.name, user.id), changes)
        return pb.UpdateConversationResponse(conversation=_to_message(conversation))


@contextmanager
def _connect_errors() -> Iterator[None]:
    """Turns the module's errors into the Connect error codes the contract promises."""
    try:
        yield
    except ValidationError as error:
        problems = "; ".join(
            f"conversation.{'.'.join(map(str, p['loc']))}: {p['msg']}" for p in error.errors()
        )
        raise ConnectError(Code.INVALID_ARGUMENT, problems) from None
    except ConversationNotFoundError:
        raise ConnectError(Code.NOT_FOUND, "The conversation does not exist.") from None
    except InvalidPageError:
        raise ConnectError(
            Code.INVALID_ARGUMENT, "page_token must come from ListConversations."
        ) from None


def _key(name: str, owner_id: UserId) -> ConversationKey:
    """The caller's conversation that `name`, which the contract checked starts with agents/,
    names. A name that is not `agents/{agent}/conversations/{thread}` names no conversation."""
    try:
        agent, collection, thread = name.removeprefix(AGENTS_PREFIX).split("/")
        if collection != "conversations":
            raise ValueError(collection)
        return ConversationKey(agent=agent, owner_id=owner_id, thread_id=UUID(thread))
    except ValueError:
        raise ConversationNotFoundError from None


def _to_message(conversation: Conversation) -> pb.Conversation:
    key = conversation.key
    last = conversation.last_message_time
    return pb.Conversation(
        name=f"{AGENTS_PREFIX}{key.agent}/conversations/{key.thread_id}",
        title=conversation.title or "",
        pinned=conversation.pinned,
        last_message_time=None if last is None else Timestamp.from_datetime(last),
    )


def _to_text_message(message: TextMessage) -> pb.Message:
    return pb.Message(
        role=ROLES[message.role],
        text=message.text,
        send_time=Timestamp.from_datetime(message.send_time),
    )
