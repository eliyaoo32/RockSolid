"""Welcomes each new client who has an email address. The welcome is a log line."""

import logging
from collections.abc import Sequence
from typing import Any

from libs.infra.runtime.executables import TasksConsumerExecutable
from libs.infra.tasks.tasks import TaskHandler
from modules.clients.domain.client_tasks import WelcomeClient

logger = logging.getLogger(__name__)


class ClientWelcomeExecutable(TasksConsumerExecutable):
    def handlers(self) -> Sequence[TaskHandler[Any]]:
        return [TaskHandler(WelcomeClient, self.welcome_client)]

    async def welcome_client(self, task: WelcomeClient) -> None:
        logger.info("welcomed client %s of %s", task.client_id, task.owner_id)
