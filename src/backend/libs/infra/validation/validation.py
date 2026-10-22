"""Checks every request against its contract's `buf.validate` rules before the handler runs, so a
handler only ever sees a request its contract allows."""

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import protovalidate
from connectrpc.code import Code
from connectrpc.errors import ConnectError
from connectrpc.request import RequestContext
from protobuf import Message


class RequestValidation:
    """A Connect interceptor that refuses, with INVALID_ARGUMENT, a request that breaks its
    contract's rules, and checks each message of a stream as it arrives. The error's message
    names each field and what is wrong with it, and its details hold the violations."""

    def check(self, request: object) -> None:
        assert isinstance(request, Message), "every Connect request is a Protobuf message"
        message: Message[Any] = request
        try:
            protovalidate.validate(message)
        except protovalidate.ValidationError as error:
            problems = "; ".join(_describe(violation.proto) for violation in error.violations)
            raise ConnectError(Code.INVALID_ARGUMENT, problems, [error.to_proto()]) from None

    async def intercept_unary[REQ, RES](
        self,
        call_next: Callable[[REQ, RequestContext[Any, Any]], Awaitable[RES]],
        request: REQ,
        ctx: RequestContext[Any, Any],
        /,
    ) -> RES:
        self.check(request)
        return await call_next(request, ctx)

    async def intercept_client_stream[REQ, RES](
        self,
        call_next: Callable[[AsyncIterator[REQ], RequestContext[Any, Any]], Awaitable[RES]],
        request: AsyncIterator[REQ],
        ctx: RequestContext[Any, Any],
        /,
    ) -> RES:
        return await call_next(self._checked(request), ctx)

    def intercept_server_stream[REQ, RES](
        self,
        call_next: Callable[[REQ, RequestContext[Any, Any]], AsyncIterator[RES]],
        request: REQ,
        ctx: RequestContext[Any, Any],
        /,
    ) -> AsyncIterator[RES]:
        self.check(request)
        return call_next(request, ctx)

    def intercept_bidi_stream[REQ, RES](
        self,
        call_next: Callable[[AsyncIterator[REQ], RequestContext[Any, Any]], AsyncIterator[RES]],
        request: AsyncIterator[REQ],
        ctx: RequestContext[Any, Any],
        /,
    ) -> AsyncIterator[RES]:
        return call_next(self._checked(request), ctx)

    async def _checked[REQ](self, requests: AsyncIterator[REQ]) -> AsyncIterator[REQ]:
        async for request in requests:
            self.check(request)
            yield request


def _describe(violation: protovalidate.ViolationPb) -> str:
    """`<field path>: <message>`, or only the message for a rule on the whole request."""
    elements = violation.field.elements if violation.field else []
    path = ".".join(element.field_name for element in elements)
    return f"{path}: {violation.message}" if path else violation.message
