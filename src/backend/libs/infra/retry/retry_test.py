from collections.abc import Callable

import pytest

from libs.infra.retry.retry import NO_RETRY, Constant, Delays, Exponential


def delays(strategy: Constant | Delays | Exponential, attempts: int) -> list[float | None]:
    return [strategy.delay_after(attempt) for attempt in range(1, attempts + 1)]


def test_constant_waits_the_same_after_each_failure_until_its_attempts_run_out() -> None:
    assert delays(Constant(seconds=5, attempts=3), 4) == [5, 5, None, None]


def test_delays_waits_each_listed_delay_in_turn_then_stops() -> None:
    assert delays(Delays(1, 10, 60), 4) == [1, 10, 60, None]


def test_exponential_doubles_each_wait_up_to_its_cap() -> None:
    assert delays(Exponential(first=2, cap=10, attempts=6), 6) == [2, 4, 8, 10, 10, None]


def test_exponential_by_default_tries_five_times() -> None:
    assert delays(Exponential(), 5) == [2, 4, 8, 16, None]


def test_no_retry_stops_after_the_first_failure() -> None:
    assert NO_RETRY.delay_after(1) is None


@pytest.mark.parametrize(
    "make", [lambda: Constant(seconds=0, attempts=2), lambda: Exponential(attempts=0)]
)
def test_rejects_a_strategy_that_cannot_work(make: Callable[[], object]) -> None:
    with pytest.raises(ValueError, match="retry"):
        make()
