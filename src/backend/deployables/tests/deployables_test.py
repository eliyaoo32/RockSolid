"""Checks that hold across every deployable. Each deployable runs as its own process, so the
runtime can check only the executables of one."""

import importlib
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

from libs.infra.runtime.executables import (
    CronExecutable,
    DomainEventsListenerExecutable,
    Executable,
    TasksConsumerExecutable,
)
from libs.infra.tasks.tasks import task_type_of
from libs.testing.runtime import build_executables

DEPLOYABLES = Path(__file__).parent.parent


def every_deployable() -> dict[str, Sequence[type[Executable]]]:
    """Each deployable's name, and the executables its `main.py` lists. A deployable is a folder
    with a `main.py`, so a new deployable is checked without being listed anywhere."""
    return {
        entry_point.parent.name: importlib.import_module(
            f"deployables.{entry_point.parent.name}.main"
        ).EXECUTABLES
        for entry_point in sorted(DEPLOYABLES.glob("*/main.py"))
    }


def test_each_deployable_lists_each_executable_once() -> None:
    repeated = {
        deployable: sorted({e.__name__ for e in executables if list(executables).count(e) > 1})
        for deployable, executables in every_deployable().items()
    }

    assert {deployable: names for deployable, names in repeated.items() if names} == {}


def test_each_cron_executable_runs_in_one_deployable() -> None:
    deployables: defaultdict[str, list[str]] = defaultdict(list)
    for deployable, executables in every_deployable().items():
        for executable in executables:
            if issubclass(executable, CronExecutable):
                deployables[executable.__name__].append(deployable)

    assert deployables, "some deployable runs cron jobs, so the check has something to check"
    assert {name: found for name, found in deployables.items() if len(found) > 1} == {}


def test_each_task_type_has_one_consumer_across_all_deployables() -> None:
    consumers: defaultdict[str, list[str]] = defaultdict(list)
    for deployable, executables in every_deployable().items():
        for executable in build_executables(executables):
            if isinstance(executable, TasksConsumerExecutable):
                for handler in executable.handlers():
                    consumers[task_type_of(handler.task)].append(
                        f"{deployable}/{type(executable).__name__}"
                    )

    assert consumers, "some deployable consumes tasks, so the check has something to check"
    assert {task: found for task, found in consumers.items() if len(found) > 1} == {}


def test_each_subscription_name_is_used_once_across_all_deployables() -> None:
    listeners: defaultdict[str, list[str]] = defaultdict(list)
    for deployable, executables in every_deployable().items():
        for executable in build_executables(executables):
            if isinstance(executable, DomainEventsListenerExecutable):
                for subscription in executable.subscriptions():
                    listeners[subscription.name].append(f"{deployable}/{type(executable).__name__}")

    assert listeners, "some deployable listens to events, so the check has something to check"
    assert {name: found for name, found in listeners.items() if len(found) > 1} == {}
