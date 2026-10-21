"""Serves one agent at `/agents/<name>`. Each request is one turn of a conversation: sign the
caller in, add their message to the conversation, run the agent on the whole conversation, keep
its answer, and end the run."""

import asyncio
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

from ag_ui.core import BaseEvent
from pydantic import ValidationError
from pydantic_ai import Agent
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.usage import UsageLimits
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from libs.infra.agents.ag_ui import ServerHistoryAdapter, newest_message, unsupported
from libs.infra.agents.deps import AgentDeps
from modules.conversations.domain.conversation import (
    MAX_RUN_TIME,
    ConversationBusyError,
    ConversationKey,
)
from modules.conversations.services.conversations import ConversationService
from modules.users.services.auth import Auth, SignInFailedError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentEndpoint:
    name: str
    agent: Agent[AgentDeps, str]
    require_auth: bool
    usage_limits: UsageLimits
    auth: Auth
    conversations: ConversationService

    @property
    def path(self) -> str:
        return f"/agents/{self.name}"

    def application(self) -> Starlette:
        return Starlette(routes=[Route(self.path, self._take_a_turn, methods=["POST"])])

    async def _take_a_turn(self, request: Request) -> Response:
        try:
            user = await self.auth.sign_in(request.headers.get("authorization"))
        except SignInFailedError as error:
            return _refusal(401, "sign_in_failed", str(error))
        if user is None and self.require_auth:
            return _refusal(401, "sign_in_required", "Sign in to talk to this agent.")
        try:
            adapter = await ServerHistoryAdapter.from_request(request, agent=self.agent)
        except ValidationError as error:
            return _refusal(400, "invalid_request", str(error))
        thread_id = _uuid(adapter.run_input.thread_id)
        if thread_id is None:
            return _refusal(400, "invalid_thread", "threadId must be a UUID.")
        if problem := unsupported(adapter):
            return _refusal(400, "unsupported_request", problem)
        key = ConversationKey(
            agent=self.name, owner_id=None if user is None else user.id, thread_id=thread_id
        )
        try:
            messages = await self.conversations.receive_message(key, newest_message(adapter))
        except ConversationBusyError:
            return _refusal(
                409,
                "conversation_busy",
                "The agent is still answering the previous message. Send yours once it ends.",
            )
        answered = asyncio.Event()

        async def keep_answer(result: AgentRunResult[str]) -> None:
            await self.conversations.append_messages(key, result.new_messages())
            answered.set()
            logger.info(
                "agent %s answered in thread %s with %d tokens",
                self.name,
                thread_id,
                result.usage.total_tokens,
            )

        events = adapter.run_stream(
            message_history=messages,
            deps=AgentDeps(None if user is None else user.id),
            usage_limits=self.usage_limits,
            timeout=MAX_RUN_TIME.total_seconds(),
            on_complete=keep_answer,
        )
        return adapter.streaming_response(self._ending_the_run(events, key, answered))

    async def _ending_the_run(
        self, events: AsyncIterator[BaseEvent], key: ConversationKey, answered: asyncio.Event
    ) -> AsyncIterator[BaseEvent]:
        """Streams the run's events, then ends the run, also when it failed or the client
        stopped it by going away."""
        try:
            async for event in events:
                yield event
        finally:
            # Shielded, so a client that goes away, which cancels the stream, still ends the run.
            await asyncio.shield(self._end_run(key, answered))

    async def _end_run(self, key: ConversationKey, answered: asyncio.Event) -> None:
        await self.conversations.end_run(key)
        if not answered.is_set():
            logger.warning(
                "agent %s ended in thread %s without an answer", self.name, key.thread_id
            )


def _uuid(value: str) -> UUID | None:
    try:
        return UUID(value)
    except ValueError:
        return None


def _refusal(status: int, code: str, message: str) -> JSONResponse:
    """Refuses a request before any run starts, as the AG-UI client reads it: an HTTP error
    with a JSON body."""
    headers = {"www-authenticate": "Bearer"} if status == 401 else None
    return JSONResponse({"code": code, "message": message}, status_code=status, headers=headers)
