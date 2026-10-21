"""What we add to Pydantic AI's AG-UI adapter, which parses the request and streams the run:
the server keeps the conversation, so only the client's newest message is read; requests that
need what agents do not support are refused; and a failure's details stay in the logs."""

import logging
from collections.abc import AsyncIterator
from functools import cached_property
from typing import Any
from uuid import UUID

from ag_ui.core import BaseEvent
from pydantic_ai.messages import ModelMessage
from pydantic_ai.ui.ag_ui import AGUIAdapter, AGUIEventStream
from starlette.responses import JSONResponse

from libs.infra.agents.deps import AgentDeps

logger = logging.getLogger(__name__)

# What a client sees when a run fails. The failure itself is logged, never sent to the client.
RUN_FAILED = "The agent could not answer this message. Send it again."


class _FailuresLoggedEventStream(AGUIEventStream[AgentDeps, str]):
    async def on_error(self, error: Exception) -> AsyncIterator[BaseEvent]:
        logger.error("agent run failed", exc_info=error)
        async for event in super().on_error(Exception(RUN_FAILED)):
            yield event


class ServerHistoryAdapter(AGUIAdapter[AgentDeps, str]):
    """Runs the agent on the history the server passes in, adding nothing the client sent."""

    @cached_property
    def messages(self) -> list[ModelMessage]:
        """None of the client's messages: the server passes the whole conversation."""
        return []

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


def newest_message(adapter: AGUIAdapter[AgentDeps, str]) -> ModelMessage:
    """The client's newest message, the one the agent answers."""
    (message,) = adapter.load_messages(
        adapter.run_input.messages[-1:], preserve_file_data=adapter.preserve_file_data
    )
    return message


def thread_id_of(adapter: AGUIAdapter[AgentDeps, str]) -> UUID:
    """The conversation's thread, which `unsupported` checked is a UUID."""
    return UUID(adapter.run_input.thread_id)


def unsupported(adapter: AGUIAdapter[AgentDeps, str]) -> str | None:
    """Why agents cannot run this request, or None when they can."""
    try:
        UUID(adapter.run_input.thread_id)
    except ValueError:
        return "threadId must be a UUID."
    messages = adapter.run_input.messages
    if not messages or messages[-1].role != "user":
        return "The newest message must be the user's."
    if adapter.run_input.tools:
        return "Agents run only their own tools, not tools the client sends."
    if adapter.run_input.resume:
        return "Agents ask for no approvals, so there is nothing to resume."
    return None


def refusal(status: int, code: str, message: str) -> JSONResponse:
    """Refuses a request before any run starts, as the AG-UI client reads it: an HTTP error
    with a JSON body."""
    headers = {"www-authenticate": "Bearer"} if status == 401 else None
    return JSONResponse({"code": code, "message": message}, status_code=status, headers=headers)
