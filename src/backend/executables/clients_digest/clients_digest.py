"""Logs, every morning, how many clients were created in the last day."""

import logging
from collections.abc import Sequence

from libs.infra.cron.cron import CronJob
from libs.infra.runtime.executables import CronExecutable
from modules.clients.services.setup import create_client_service, migrate_schema

logger = logging.getLogger(__name__)


class ClientsDigestExecutable(CronExecutable):
    migrations = (migrate_schema,)

    def jobs(self) -> Sequence[CronJob]:
        clients = create_client_service(self.infra.database, self.infra.now)

        async def log_new_clients() -> None:
            count = await clients.count_created_in_the_last_day()
            logger.info("%d clients were created in the last day", count)

        return [CronJob("0 7 * * *", log_new_clients)]
