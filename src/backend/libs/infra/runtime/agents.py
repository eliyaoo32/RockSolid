"""Serves an agent over AG-UI. Each request signs the caller in, continues the caller's
conversation from the history the server keeps, streams the agent's answer, and keeps the
conversation once the answer is complete.

The client sends its whole thread with every run. Only its newest message is used: the server
keeps everything said before it, so a client cannot rewrite what the agent was told.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from functools import cached_property
from typing import Any
from uuid import UUID

import pydantic_ai
from ag_ui.core import BaseEvent
from pydantic import ValidationError
from pydantic_ai import Agent, ModelRetry
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from pydantic_ai.ui.ag_ui import AGUIAdapter, AGUIEventStream
from pydantic_ai.usage import UsageLimits
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from modules.conversations.domain.conversation import (
    ConversationBusyError,
    ConversationKey,
    RunNotActiveError,
)
from modules.conversations.services.conversations import ConversationService
from modules.users.domain.user import UserId
from modules.users.services.auth import Auth, SignInFailedError

logger = logging.getLogger(__name__)

# Logs are JSON lines; Pydantic AI's first-run banner is not one.
pydantic_ai.BANNER_ENABLED = False

# What a client sees when a run fails. The failure itself is logged, never sent to the client.
RUN_FAILED = "The agent could not answer this message. Send it again."


@dataclass(frozen=True)
class AgentDeps:
    """What every run of an agent gets: who is calling, or None for an anonymous caller."""

    user_id: UserId | None

    def signed_in_user_id(self) -> UserId:
        """The caller's user ID, for a tool that acts as the user. In an anonymous run, tells
        the model that the user must sign in first."""
        if self.user_id is None:
            raise ModelRetry("The user is not signed in. Ask them to sign in first.")
        return self.user_id


class _FailuresLoggedEventStream(AGUIEventStream[AgentDeps, str]):
    async def on_error(self, error: Exception) -> AsyncIterator[BaseEvent]:
        logger.error("agent run failed", exc_info=error)
        async for event in super().on_error(Exception(RUN_FAILED)):
            yield event


class _ServerHistoryAdapter(AGUIAdapter[AgentDeps, str]):
    @cached_property
    def messages(self) -> list[ModelMessage]:
        """Only the client's newest message; the server keeps everything said before it."""
        return self.load_messages(
            self.run_input.messages[-1:], preserve_file_data=self.preserve_file_data
        )

    @cached_property
    def state(self) -> dict[str, Any] | None:
        """No shared state: agents keep what they know in their conversations."""
        return None

    def build_event_stream(self) -> AGUIEventStream[AgentDeps, str]:
        return _FailuresLoggedEventStream(
            self.run_input,
            accept=self.accept,
            ag_ui_version=self.ag_ui_version,
            manage_system_prompt=self.manage_system_prompt,
            preserve_file_data=self.preserve_file_data,
        )


@dataclass(frozen=True)
class AgentEndpoint:
    """One agent, served at `/agents/<name>`."""

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
        return Starlette(routes=[Route(self.path, self._run, methods=["POST"])])

    async def _run(self, request: Request) -> Response:
        try:
            user = await self.auth.sign_in(request.headers.get("authorization"))
        except SignInFailedError as error:
            return _refusal(401, "sign_in_failed", str(error))
        if user is None and self.require_auth:
            return _refusal(401, "sign_in_required", "Sign in to talk to this agent.")
        try:
            adapter = await _ServerHistoryAdapter.from_request(request, agent=self.agent)
        except ValidationError as error:
            return _refusal(400, "invalid_request", str(error))
        thread_id = _thread_id(adapter)
        if thread_id is None:
            return _refusal(400, "invalid_thread", "threadId must be a UUID.")
        if problem := _unsupported(adapter):
            return _refusal(400, "unsupported_request", problem)
        key = ConversationKey(
            agent=self.name, owner_id=None if user is None else user.id, thread_id=thread_id
        )
        try:
            started = await self.conversations.start_run(key)
        except ConversationBusyError:
            return _refusal(
                409,
                "conversation_busy",
                "This conversation is answering another message. Send yours again once it ends.",
            )

        async def keep_conversation(result: AgentRunResult[str]) -> None:
            history = ModelMessagesTypeAdapter.dump_json(result.all_messages()).decode()
            try:
                await self.conversations.finish_run(key, started.run_id, history)
            except RunNotActiveError:
                logger.warning(
                    "agent %s run %s finished after another run took thread %s over",
                    self.name,
                    started.run_id,
                    key.thread_id,
                )
                return
            logger.info(
                "agent %s answered in thread %s, run %s, with %d tokens",
                self.name,
                key.thread_id,
                started.run_id,
                result.usage.total_tokens,
            )

        events = adapter.run_stream(
            message_history=ModelMessagesTypeAdapter.validate_json(started.history),
            deps=AgentDeps(None if user is None else user.id),
            usage_limits=self.usage_limits,
            on_complete=keep_conversation,
        )
        return adapter.streaming_response(self._ending_the_run(events, key, started.run_id))

    async def _ending_the_run(
        self, events: AsyncIterator[BaseEvent], key: ConversationKey, run_id: UUID
    ) -> AsyncIterator[BaseEvent]:
        """Streams the run's events. A run that ends without keeping its conversation, such as
        when it fails or the client goes away, frees the conversation and keeps its history."""
        try:
            async for event in events:
                yield event
        finally:
            # Shielded, so a client that goes away, which cancels the stream, still frees it.
            await asyncio.shield(self._abandon_unless_finished(key, run_id))

    async def _abandon_unless_finished(self, key: ConversationKey, run_id: UUID) -> None:
        if await self.conversations.abandon_run(key, run_id):
            logger.warning(
                "agent %s run %s in thread %s ended without an answer",
                self.name,
                run_id,
                key.thread_id,
            )


def _thread_id(adapter: AGUIAdapter[AgentDeps, str]) -> UUID | None:
    try:
        return UUID(adapter.run_input.thread_id)
    except ValueError:
        return None


def _unsupported(adapter: AGUIAdapter[AgentDeps, str]) -> str | None:
    """Why the agent cannot run this request, or None when it can."""
    messages = adapter.run_input.messages
    if not messages or messages[-1].role != "user":
        return "The newest message must be the user's."
    if adapter.run_input.tools:
        return "Agents run only their own tools, not tools the client sends."
    if adapter.run_input.resume:
        return "Agents ask for no approvals, so there is nothing to resume."
    return None


def _refusal(status: int, code: str, message: str) -> JSONResponse:
    """Refuses a request before any run starts, as the AG-UI client reads it: an HTTP error
    with a JSON body."""
    headers = {"www-authenticate": "Bearer"} if status == 401 else None
    return JSONResponse({"code": code, "message": message}, status_code=status, headers=headers)
