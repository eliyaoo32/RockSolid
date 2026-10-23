"""A scripted model for the clients assistant: it turns a user's message into the tool call a
real model would make, and answers with what the tool returned."""

import json
from collections.abc import AsyncIterator

from pydantic_ai.messages import ModelMessage, RetryPromptPart, ToolReturnPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, DeltaToolCalls, FunctionModel


async def _answer(
    messages: list[ModelMessage], info: AgentInfo
) -> AsyncIterator[str | DeltaToolCalls]:
    """`list <filter>` lists clients, and `add <name> | <email>` adds one. A tool's result or
    complaint becomes the answer."""
    last = messages[-1].parts[-1]
    if isinstance(last, ToolReturnPart):
        yield f"Done: {last.model_response_str()}"
    elif isinstance(last, RetryPromptPart):
        yield f"Could not: {last.model_response()}"
    else:
        assert isinstance(last, UserPromptPart), "a run starts from the user's message"
        command, _, rest = str(last.content).partition(" ")
        if command == "list":
            yield {0: DeltaToolCall(name="list_clients", json_args=json.dumps({"filter": rest}))}
        else:
            name, _, email = (part.strip() for part in rest.partition("|"))
            arguments = {"display_name": name, "email": email or None}
            yield {0: DeltaToolCall(name="create_client", json_args=json.dumps(arguments))}


def scripted_model() -> FunctionModel:
    return FunctionModel(stream_function=_answer)
