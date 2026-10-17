from collections.abc import Sequence
from typing import Any, ClassVar

import pytest
from pydantic import BaseModel

from libs.infra.events.events import Subscription
from libs.infra.runtime.executables import DomainEventsListenerExecutable
from libs.testing.runtime import run_executables


class Greeted(BaseModel):
    event_type: ClassVar[str] = "tests.Greeted"


class Greeters(DomainEventsListenerExecutable):
    def subscriptions(self) -> Sequence[Subscription[Any]]:
        return [Subscription("welcome", Greeted, self.welcome)]

    async def welcome(self, event: Greeted) -> None: ...


class MoreGreeters(Greeters):
    """Reuses the subscription name, so the executables cannot start together."""


async def test_raises_why_the_executables_could_not_start(database_url: str) -> None:
    running = run_executables([Greeters, MoreGreeters], database_url)

    with pytest.raises(ValueError, match="two subscriptions are named welcome"):
        await running.__aenter__()
