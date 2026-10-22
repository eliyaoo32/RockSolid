"""Talks to an agent over AG-UI the way a frontend does, for tests: one POST per message, with
the reply streamed back as server-sent events."""

import json
from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import httpx


@dataclass(frozen=True)
class AgentReply:
    status: int
    # The run's AG-UI events, in order, when the agent ran.
    events: list[dict[str, Any]]
    # The refusal's JSON body, when the request was refused before any run started.
    refusal: dict[str, Any] | None

    @property
    def text(self) -> str:
        """All the text the agent streamed."""
        return "".join(e["delta"] for e in self.events if e["type"] == "TEXT_MESSAGE_CONTENT")

    @property
    def tool_calls(self) -> list[str]:
        """The names of the tools the agent called, in order."""
        return [e["toolCallName"] for e in self.events if e["type"] == "TOOL_CALL_START"]

    @property
    def error(self) -> str | None:
        """The message of the run's error, or None when the run did not fail."""
        return next((e["message"] for e in self.events if e["type"] == "RUN_ERROR"), None)


def user_message(text: str) -> dict[str, Any]:
    return {"id": uuid4().hex, "role": "user", "content": text}


def assistant_message(text: str) -> dict[str, Any]:
    return {"id": uuid4().hex, "role": "assistant", "content": text}


class AgentClient:
    """Sends messages to the agents a test runs, on `port`."""

    def __init__(self, port: int) -> None:
        self._url = f"http://127.0.0.1:{port}"

    async def send(
        self,
        agent: str,
        thread_id: str,
        text: str,
        *,
        token: str | None = None,
        earlier: Sequence[Mapping[str, Any]] = (),
        **fields: Any,
    ) -> AgentReply:
        """Sends `text` as the newest message of the thread, after the `earlier` messages a
        frontend would resend, and waits for the whole reply. `fields` replace fields of the
        AG-UI run input, such as `tools`."""
        async with self.stream(
            agent, thread_id, text, token=token, earlier=earlier, **fields
        ) as response:
            body = await response.aread()
        if response.status_code != 200:
            return AgentReply(response.status_code, [], json.loads(body))
        events = [
            json.loads(line.removeprefix("data: "))
            for line in body.decode().splitlines()
            if line.startswith("data: ")
        ]
        return AgentReply(response.status_code, events, None)

    @asynccontextmanager
    async def stream(
        self,
        agent: str,
        thread_id: str,
        text: str,
        *,
        token: str | None = None,
        earlier: Sequence[Mapping[str, Any]] = (),
        **fields: Any,
    ) -> AsyncIterator[httpx.Response]:
        """Sends a message and yields the response as it streams, for a test that stops reading
        part way, as a client that goes away does."""
        run_input: dict[str, Any] = {
            "threadId": thread_id,
            "runId": uuid4().hex,
            "state": {},
            "messages": [*earlier, user_message(text)],
            "tools": [],
            "context": [],
            "forwardedProps": {},
        } | fields
        headers = {"accept": "text/event-stream"}
        if token is not None:
            headers["authorization"] = f"Bearer {token}"
        async with (
            httpx.AsyncClient(base_url=self._url, timeout=10) as http,
            http.stream("POST", f"/agents/{agent}", json=run_input, headers=headers) as response,
        ):
            yield response
