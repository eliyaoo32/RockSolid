"""The examples deployable: the example executables, which run beside the framework's `app`.
Commands: `migrate` and `serve`."""

import asyncio
import sys

from executables.client_activity.client_activity import ClientActivityExecutable
from executables.client_welcome.client_welcome import ClientWelcomeExecutable
from executables.clients_api.clients_api import ClientsApiExecutable
from executables.clients_assistant.clients_assistant import ClientsAssistantExecutable
from executables.clients_digest.clients_digest import ClientsDigestExecutable
from libs.infra.runtime.runtime import run

EXECUTABLES = [
    ClientsApiExecutable,
    ClientsAssistantExecutable,
    ClientsDigestExecutable,
    ClientActivityExecutable,
    ClientWelcomeExecutable,
]

if __name__ == "__main__":
    asyncio.run(run(sys.argv[1:], EXECUTABLES))
