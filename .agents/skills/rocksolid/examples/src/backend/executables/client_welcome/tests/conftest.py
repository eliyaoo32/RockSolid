from executables.client_welcome.tests.framework.fixtures import (
    driver,
    driver_without_mail_api_key,
)
from libs.testing.postgres import database_url

__all__ = ["database_url", "driver", "driver_without_mail_api_key"]
