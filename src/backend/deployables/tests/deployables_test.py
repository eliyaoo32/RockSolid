"""Checks that hold across every deployable. Each deployable runs as its own process, so the
runtime can check only the executables of one. RockSolid's examples give each check something to
check (`examples_test.py` in the rocksolid skill's examples)."""

from collections import defaultdict

from libs.infra.runtime.executables import (
    CronExecutable,
    DomainEventsListenerExecutable,
    TasksConsumerExecutable,
)
from libs.infra.tasks.tasks import task_type_of
from libs.testing.deployables import every_deployable, http_routes
from libs.testing.runtime import build_executables


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

    assert {task: found for task, found in consumers.items() if len(found) > 1} == {}


def test_each_subscription_name_is_used_once_across_all_deployables() -> None:
    listeners: defaultdict[str, list[str]] = defaultdict(list)
    for deployable, executables in every_deployable().items():
        for executable in build_executables(executables):
            if isinstance(executable, DomainEventsListenerExecutable):
                for subscription in executable.subscriptions():
                    listeners[subscription.name].append(f"{deployable}/{type(executable).__name__}")

    assert {name: found for name, found in listeners.items() if len(found) > 1} == {}


def test_each_http_route_is_served_by_one_deployable() -> None:
    servers: defaultdict[str, list[str]] = defaultdict(list)
    for deployable, executables in every_deployable().items():
        for route in http_routes(executables):
            servers[route].append(deployable)

    assert "/users.v1.UsersService" in servers, "the check reads the routes the services declare"
    assert {route: found for route, found in servers.items() if len(found) > 1} == {}
