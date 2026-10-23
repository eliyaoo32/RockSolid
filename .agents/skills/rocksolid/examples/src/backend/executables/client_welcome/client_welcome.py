"""Welcomes each new client who has an email address, with an email the mail API sends."""

from collections.abc import Sequence
from typing import Any

from libs.infra.retry.retry import NonRetryableError
from libs.infra.runtime.executables import TasksConsumerExecutable
from libs.infra.tasks.tasks import TaskHandler
from modules.clients.domain.client_tasks import WelcomeClient
from modules.clients.services.clients import MailNotConfiguredError
from modules.clients.services.setup import create_client_service, migrate_schema


class ClientWelcomeExecutable(TasksConsumerExecutable):
    migrations = (migrate_schema,)

    def handlers(self) -> Sequence[TaskHandler[Any]]:
        clients = create_client_service(self.infra.database, self.infra.now)

        async def welcome_client(task: WelcomeClient) -> None:
            try:
                await clients.welcome(task.owner_id, task.client_id)
            except MailNotConfiguredError as error:
                raise NonRetryableError(str(error)) from error

        return [TaskHandler(WelcomeClient, welcome_client)]
