"""Talks to an agent the way the frontend does: over AG-UI, with a sign-in token, for E2E tests of
agents. A project with an agent copies this file into `src/tests/e2e/framework/`."""

import json
from dataclasses import dataclass
from uuid import uuid4

import httpx

from e2e.framework.system import System


@dataclass(frozen=True)
class AgentAnswer:
    status: int
    # The text the agent streamed, when it ran.
    text: str


def talk_to_agent(
    system: System, agent: str, thread_id: str, text: str, token: str | None
) -> AgentAnswer:
    """Sends `text` to an agent over AG-UI, as the newest message of the thread, and returns its
    answer once it has streamed."""
    path = f"/agents/{agent}"
    deployable = system.serving(path)
    assert deployable is not None, f"No deployable serves {path}"
    run_input: dict[str, object] = {
        "threadId": thread_id,
        "runId": uuid4().hex,
        "state": {},
        "messages": [{"id": uuid4().hex, "role": "user", "content": text}],
        "tools": [],
        "context": [],
        "forwardedProps": {},
    }
    headers = {"accept": "text/event-stream"}
    if token is not None:
        headers["authorization"] = f"Bearer {token}"
    response = httpx.post(deployable.url + path, json=run_input, headers=headers, timeout=30)
    events = [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    streamed = "".join(e["delta"] for e in events if e["type"] == "TEXT_MESSAGE_CONTENT")
    return AgentAnswer(response.status_code, streamed)
