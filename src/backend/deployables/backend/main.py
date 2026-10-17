"""The backend deployable: the executables it runs. Commands: `migrate` and `serve`."""

import asyncio
import sys

from executables.client_activity.client_activity import ClientActivityExecutable
from executables.clients_api.clients_api import ClientsApiExecutable
from executables.clients_digest.clients_digest import ClientsDigestExecutable
from libs.infra.runtime.runtime import run

EXECUTABLES = [ClientsApiExecutable, ClientsDigestExecutable, ClientActivityExecutable]

if __name__ == "__main__":
    asyncio.run(run(sys.argv[1:], EXECUTABLES))
