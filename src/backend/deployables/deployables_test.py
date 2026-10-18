"""Checks that hold across every deployable. Each deployable runs as its own process, so the
runtime checks only the executables of one."""

from pathlib import Path

from deployables.backend.main import EXECUTABLES as BACKEND
from libs.infra.runtime.runtime import collect_background_work
from libs.testing.runtime import build_executables

DEPLOYABLES = {"backend": BACKEND}


def test_checks_every_deployable() -> None:
    entry_points = Path(__file__).parent.glob("*/main.py")

    assert set(DEPLOYABLES) == {entry_point.parent.name for entry_point in entry_points}


def test_no_two_deployables_handle_one_task_type_or_share_a_subscription_name() -> None:
    executables = [executable for listed in DEPLOYABLES.values() for executable in listed]

    work = collect_background_work(build_executables(executables))

    assert work.handlers, "the deployables handle tasks, so the check has something to check"
