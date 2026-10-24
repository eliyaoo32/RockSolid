"""Agents to talk to, so the conversations the API lists exist: each echoes the user's message."""

from collections.abc import AsyncIterator

from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from libs.infra.agents.deps import AgentDeps
from libs.infra.runtime.executables import AgentExecutable


async def _echo(messages: list[ModelMessage], info: AgentInfo) -> AsyncIterator[str]:
    last = messages[-1].parts[-1]
    assert isinstance(last, UserPromptPart), "a run starts from the user's message"
    yield f"You said: {last.content}"


def echoing_model() -> FunctionModel:
    return FunctionModel(stream_function=_echo)


class Assistant(AgentExecutable):
    name = "assistant"
    require_auth = True

    def agent(self) -> Agent[AgentDeps, str]:
        return Agent(self.infra.models.ollama("echo"), deps_type=AgentDeps)


class Helper(Assistant):
    """A second agent, whose conversations are listed apart from the assistant's."""

    name = "helper"
