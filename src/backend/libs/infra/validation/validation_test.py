from collections.abc import AsyncIterator
from typing import Any

import pytest
from connectrpc.code import Code
from connectrpc.errors import ConnectError
from protobuf import Message
from protovalidate import ViolationsPb

from clients.v1 import clients_pb as pb
from libs.infra.validation.validation import RequestValidation

VALID = pb.CreateClientRequest(client=pb.Client(display_name="Avi Cohen"))
INVALID = pb.CreateClientRequest(client=pb.Client(display_name="Avi Cohen", email="not-an-email"))
CTX: Any = object()


async def handled(request: Message, ctx: object) -> str:
    return "handled"


async def handled_stream(requests: AsyncIterator[Message], ctx: object) -> str:
    return f"handled {len([request async for request in requests])}"


async def answered(request: Message, ctx: object) -> AsyncIterator[str]:
    yield "answer"


async def echoed(requests: AsyncIterator[Message], ctx: object) -> AsyncIterator[str]:
    async for _ in requests:
        yield "echo"


async def stream_of(*requests: Message) -> AsyncIterator[Message]:
    for request in requests:
        yield request


def test_refuses_a_request_that_breaks_its_contract_naming_each_field() -> None:
    request = pb.CreateClientRequest(client=pb.Client(display_name="x" * 201, email="nope"))

    with pytest.raises(ConnectError) as refused:
        RequestValidation().check(request)

    assert refused.value.code == Code.INVALID_ARGUMENT
    assert refused.value.message == (
        "client.display_name: must be at most 200 characters; "
        "client.email: must be a valid email address"
    )
    (detail,) = refused.value.details
    violations = detail.value(ViolationsPb)
    assert violations is not None, "the details hold the violations"
    assert [v.rule_id for v in violations.violations] == ["string.max_len", "string.email"]


def test_names_no_field_for_a_rule_on_the_whole_request() -> None:
    with pytest.raises(ConnectError) as refused:
        RequestValidation().check(pb.CreateClientRequest(client=pb.Client()))

    assert refused.value.message == "client.display_name is required"


async def test_passes_a_valid_unary_request_on_and_refuses_an_invalid_one() -> None:
    validation = RequestValidation()

    assert await validation.intercept_unary(handled, VALID, CTX) == "handled"
    with pytest.raises(ConnectError):
        await validation.intercept_unary(handled, INVALID, CTX)


async def test_checks_every_message_of_a_client_stream() -> None:
    validation = RequestValidation()

    assert (
        await validation.intercept_client_stream(handled_stream, stream_of(VALID, VALID), CTX)
        == "handled 2"
    )
    with pytest.raises(ConnectError):
        await validation.intercept_client_stream(handled_stream, stream_of(VALID, INVALID), CTX)


async def test_checks_the_request_of_a_server_stream() -> None:
    validation = RequestValidation()

    assert [a async for a in validation.intercept_server_stream(answered, VALID, CTX)] == ["answer"]
    with pytest.raises(ConnectError):
        validation.intercept_server_stream(answered, INVALID, CTX)


async def test_checks_every_message_of_a_bidi_stream() -> None:
    validation = RequestValidation()
    echoes = validation.intercept_bidi_stream(echoed, stream_of(VALID, VALID), CTX)

    assert [e async for e in echoes] == ["echo", "echo"]
    with pytest.raises(ConnectError):
        [e async for e in validation.intercept_bidi_stream(echoed, stream_of(INVALID), CTX)]
