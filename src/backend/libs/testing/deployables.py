"""Finds every deployable, for tests that check or run all of them."""

import importlib
from collections.abc import Sequence
from pathlib import Path

from libs.infra.runtime.executables import Executable, HttpExecutable
from libs.testing.runtime import build_executables

DEPLOYABLES = Path(__file__).parents[2] / "deployables"


def every_deployable() -> dict[str, Sequence[type[Executable]]]:
    """Each deployable's name, and the executables its `main.py` lists. A deployable is a folder
    with a `main.py`, so a new deployable is found without being listed anywhere."""
    return {
        entry_point.parent.name: importlib.import_module(
            f"deployables.{entry_point.parent.name}.main"
        ).EXECUTABLES
        for entry_point in sorted(DEPLOYABLES.glob("*/main.py"))
    }


def http_routes(executables: Sequence[type[Executable]]) -> list[str]:
    """The path prefixes a deployable's HTTP server answers, such as `/users.v1.UsersService`."""
    return [
        prefix
        for executable in build_executables(executables)
        if isinstance(executable, HttpExecutable)
        for prefix in executable.routes()
    ]
