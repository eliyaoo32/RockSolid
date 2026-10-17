"""The kinds of executable the runtime runs. An executable is a class: the runtime reads its
migrations without building it, and builds it once per process with the shared infra."""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Protocol

from connectrpc.interceptor import MetadataInterceptor
from sqlalchemy.ext.asyncio import AsyncEngine

from modules.users.services.auth import Auth

type Scope = MutableMapping[str, Any]
type Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
type Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]
type ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]
type Migration = Callable[[AsyncEngine], Awaitable[None]]


@dataclass(frozen=True)
class Infra:
    """What every executable in the process shares."""

    engine: AsyncEngine
    auth: Auth
    now: Callable[[], datetime]


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
    """An executable that works in the background instead of serving HTTP. Not run yet: each
    background type gets its behavior with the first feature that needs it."""


class CronSchedulerExecutable(BackgroundExecutable):
    """Runs jobs at fixed times or intervals."""


class TasksConsumerExecutable(BackgroundExecutable):
    """Takes commands from a queue and runs each one exactly once, with retries."""


class DomainEventsListenerExecutable(BackgroundExecutable):
    """Reacts to domain events published by any module."""


class RpcApplication(Protocol):
    """A generated ConnectRPC ASGI application, such as `ClientsServiceASGIApplication`."""

    @property
    def path(self) -> str: ...

    async def __call__(self, scope: Scope, receive: Receive, send: Send, /) -> None: ...


class RpcServiceExecutable(HttpExecutable):
    """Serves one ConnectRPC service. Every call must be signed in."""

    def __init__(self, infra: Infra) -> None:
        super().__init__(infra)
        self._application = self.application(interceptors=[infra.auth])

    @abstractmethod
    def application(self, interceptors: Sequence[MetadataInterceptor[Any]]) -> RpcApplication:
        """Builds the generated application around the service, with these interceptors."""

    def routes(self) -> Mapping[str, ASGIApp]:
        return {self._application.path: self._application}
