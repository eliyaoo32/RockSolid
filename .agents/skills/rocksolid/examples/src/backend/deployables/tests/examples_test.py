"""The examples give each check across deployables (`deployables_test.py`) something to check."""

from libs.infra.runtime.executables import (
    CronExecutable,
    DomainEventsListenerExecutable,
    TasksConsumerExecutable,
)
from libs.testing.deployables import every_deployable
from libs.testing.runtime import build_executables


def test_the_examples_run_cron_jobs_consume_tasks_and_listen_to_events() -> None:
    executables = every_deployable()["examples"]
    built = build_executables(executables)

    assert any(issubclass(e, CronExecutable) for e in executables)
    assert any(isinstance(e, TasksConsumerExecutable) for e in built)
    assert any(isinstance(e, DomainEventsListenerExecutable) for e in built)
