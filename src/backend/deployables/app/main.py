"""The app deployable: the executables it runs. Commands: `migrate` and `serve`."""

import asyncio
import sys

from executables.users_api.users_api import UsersApiExecutable
from libs.infra.runtime.runtime import run

EXECUTABLES = [
    UsersApiExecutable,
]

if __name__ == "__main__":
    asyncio.run(run(sys.argv[1:], EXECUTABLES))
