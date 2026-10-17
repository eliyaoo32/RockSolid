"""Logs every client created, so client activity can be followed in the logs."""

import logging
from collections.abc import Sequence
from typing import Any

from libs.infra.events.events import Subscription
from libs.infra.runtime.executables import DomainEventsListenerExecutable
from modules.clients.domain.client_events import ClientCreated

logger = logging.getLogger(__name__)


class ClientActivityExecutable(DomainEventsListenerExecutable):
    def subscriptions(self) -> Sequence[Subscription[Any]]:
        return [Subscription("log_new_client", ClientCreated, self.log_new_client)]

    async def log_new_client(self, event: ClientCreated) -> None:
        # The client's name is personal data, so only IDs are logged.
        logger.info("client %s was created by %s", event.client_id, event.owner_id)
