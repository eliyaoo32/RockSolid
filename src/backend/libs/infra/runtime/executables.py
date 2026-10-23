"""The kinds of executable the runtime runs. An executable is a class: the runtime reads its
migrations without building it, and builds it once per process with the shared infra."""

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Protocol

from ag_ui.core import BaseEvent
from connectrpc.interceptor import (
    BidiStreamInterceptor,
    ClientStreamInterceptor,
    MetadataInterceptor,
    ServerStreamInterceptor,
    UnaryInterceptor,
)
from pydantic import ValidationError
from pydantic_ai import Agent
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.usage import UsageLimits
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from libs.infra.agents.ag_ui import (
    ServerHistoryAdapter,
    newest_message,
    refusal,
    thread_id_of,
    unsupported,
)
from libs.infra.agents.deps import AgentDeps
from libs.infra.cron.cron import CronJob
from libs.infra.events.events import Subscription
from libs.infra.llm.models import Models
from libs.infra.tasks.tasks import TaskHandler
from libs.infra.validation.validation import RequestValidation
from modules.conversations.domain.conversation import MAX_RUN_TIME, ConversationKey
from modules.conversations.services.errors import ConversationBusyError
from modules.conversations.services.setup import create_conversation_service
from modules.users.services.auth import Auth
from modules.users.services.errors import SignInFailedError

type Scope = MutableMapping[str, Any]
type Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
type Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]
type ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]
type Migration = Callable[[AsyncEngine], Awaitable[None]]
# Connect's `Interceptor`, with the metadata interceptor's type filled in.
type RpcInterceptor = (
    MetadataInterceptor[Any]
    | UnaryInterceptor
    | ClientStreamInterceptor
    | ServerStreamInterceptor
    | BidiStreamInterceptor
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Infra:
    """What every executable in the process shares."""

    # The database: its connection pool, shared by everything in the process.
    database: AsyncEngine
    auth: Auth
    now: Callable[[], datetime]
    # The language models agents choose from.
    models: Models


class Executable:
    # The module schemas this executable needs; `migrate` applies each once per deployable.
    migrations: ClassVar[Sequence[Migration]] = ()

    def __init__(self, infra: Infra) -> None:
        self.infra = infra


class HttpExecutable(Executable, ABC):
    """An executable the runtime mounts on the deployable's one HTTP server."""

    @abstractmethod
    def routes(self) -> Mapping[str, ASGIApp]:
        """The path prefixes this executable serves, and the app for each."""


class BackgroundExecutable(Executable):
    """An executable that works in the background instead of serving HTTP. Each background type
    gets its behavior with the first feature that needs it."""


class CronExecutable(BackgroundExecutable, ABC):
    """Runs jobs on schedules. One executable holds as many jobs as its business area needs."""

    @abstractmethod
    def jobs(self) -> Sequence[CronJob]:
        """The executable's jobs. The runtime calls it once, at startup."""


class TasksConsumerExecutable(BackgroundExecutable, ABC):
    """Runs queued tasks. One executable holds as many handlers as its business area needs, and
    each task type has one handler across every deployable."""

    @abstractmethod
    def handlers(self) -> Sequence[TaskHandler[Any]]:
        """The executable's handlers. The runtime calls it once, at startup."""


class DomainEventsListenerExecutable(BackgroundExecutable, ABC):
    """Reacts to domain events published by any module. One executable holds as many
    subscriptions as its business area needs."""

    @abstractmethod
    def subscriptions(self) -> Sequence[Subscription[Any]]:
        """The executable's subscriptions. The runtime calls it once, at startup."""


class RpcApplication(Protocol):
    """A generated ConnectRPC ASGI application, such as `ClientsServiceASGIApplication`."""

    @property
    def path(self) -> str: ...

    async def __call__(self, scope: Scope, receive: Receive, send: Send, /) -> None: ...


class RpcServiceExecutable(HttpExecutable):
    """Serves one ConnectRPC service. Every call must be signed in, and every request must keep
    its contract's `buf.validate` rules."""

    def __init__(self, infra: Infra) -> None:
        super().__init__(infra)
        self._application = self.application(interceptors=[infra.auth, RequestValidation()])

    @abstractmethod
    def application(self, interceptors: Sequence[RpcInterceptor]) -> RpcApplication:
        """Builds the generated application around the service, with these interceptors."""

    def routes(self) -> Mapping[str, ASGIApp]:
        return {self._application.path: self._application}


class AgentExecutable(HttpExecutable, ABC):
    """Serves one Pydantic AI agent over AG-UI at `/agents/<name>`. Each request is one turn of
    a conversation the server keeps: sign the caller in, add their message, run the agent on the
    whole conversation, and add its answer."""

    # Names the agent's route and its conversations, so it stays the same across releases.
    name: ClassVar[str]
    # True: every caller must sign in. False: anonymous callers talk to the agent too.
    require_auth: ClassVar[bool]
    # Bounds one run, so a model that keeps calling tools cannot run, or cost, without end.
    usage_limits: ClassVar[UsageLimits] = UsageLimits(request_limit=20, tool_calls_limit=50)

    def __init__(self, infra: Infra) -> None:
        super().__init__(infra)
        self.served_agent = self.agent()
        self._conversations = create_conversation_service(infra.database, infra.now)

    @abstractmethod
    def agent(self) -> Agent[AgentDeps, str]:
        """Builds the agent, with its model from `infra.models`, its instructions, and its tools.
        The runtime calls it once, at startup."""

    @property
    def path(self) -> str:
        return f"/agents/{self.name}"

    def routes(self) -> Mapping[str, ASGIApp]:
        return {self.path: Starlette(routes=[Route(self.path, self._answer, methods=["POST"])])}

    async def _answer(self, request: Request) -> Response:
        """One turn of the conversation."""
        try:
            user = await self.infra.auth.sign_in(request.headers.get("authorization"))
        except SignInFailedError as error:
            return refusal(401, "sign_in_failed", str(error))
        if user is None and self.require_auth:
            return refusal(401, "sign_in_required", "Sign in to talk to this agent.")
        try:
            adapter = await ServerHistoryAdapter.from_request(request, agent=self.served_agent)
        except ValidationError as error:
            return refusal(400, "invalid_request", str(error))
        if problem := unsupported(adapter):
            return refusal(400, "unsupported_request", problem)
        user_id = None if user is None else user.id
        key = ConversationKey(agent=self.name, owner_id=user_id, thread_id=thread_id_of(adapter))
        try:
            conversation = await self._conversations.receive_message(key, newest_message(adapter))
        except ConversationBusyError:
            return refusal(
                409,
                "conversation_busy",
                "The agent is still answering the previous message. Send yours once it ends.",
            )

        async def add_the_answer(result: AgentRunResult[str]) -> None:
            await self._conversations.append_messages(key, result.new_messages())

        events = adapter.run_stream(
            message_history=conversation,
            deps=AgentDeps(user_id),
            usage_limits=self.usage_limits,
            timeout=MAX_RUN_TIME.total_seconds(),
            on_complete=add_the_answer,
        )
        return adapter.streaming_response(self._stopping_unless_answered(events, key))

    async def _stopping_unless_answered(
        self, events: AsyncIterator[BaseEvent], key: ConversationKey
    ) -> AsyncIterator[BaseEvent]:
        """Streams the run's events. A run that ends without an answer, because it failed or the
        client stopped it by going away, is stopped, so the user can send their next message."""
        try:
            async for event in events:
                yield event
        finally:
            # Shielded, so a client that goes away, which cancels the stream, still stops it.
            await asyncio.shield(self._stop_unless_answered(key))

    async def _stop_unless_answered(self, key: ConversationKey) -> None:
        if await self._conversations.stop(key):
            logger.warning(
                "agent %s stopped in thread %s without an answer", self.name, key.thread_id
            )
