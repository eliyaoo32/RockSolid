"""The backend deployable: the executables it runs. Commands: `migrate` and `serve`."""

import asyncio
import sys

from executables.clients_api.clients_api import ClientsApiExecutable
from libs.infra.runtime.runtime import run

EXECUTABLES = [ClientsApiExecutable]

if __name__ == "__main__":
    asyncio.run(run(sys.argv[1:], EXECUTABLES))
