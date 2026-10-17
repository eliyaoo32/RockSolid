"""Retry strategies: after a failed attempt, how long to wait before the next one, or to stop.

Raising `NonRetryableError` stops at once, whatever the strategy, for a failure that trying
again cannot fix, such as an event about a record that no longer exists.
"""

from dataclasses import dataclass
from typing import Protocol


class NonRetryableError(Exception):
    """A failure that trying again cannot fix."""


class RetryStrategy(Protocol):
    def delay_after(self, attempt: int) -> float | None:
        """Seconds to wait after failed attempt number `attempt` (from 1), or None to stop."""
        ...


@dataclass(frozen=True)
class Constant:
    """Waits the same `seconds` after each failure, for `attempts` attempts in all."""

    seconds: float
    attempts: int

    def __post_init__(self) -> None:
        if self.seconds <= 0 or self.attempts < 1:
            raise ValueError("a constant retry needs seconds above 0 and at least 1 attempt")

    def delay_after(self, attempt: int) -> float | None:
        return self.seconds if attempt < self.attempts else None


class Delays:
    """Waits each listed delay in turn, then stops: `Delays(1, 10, 60)` tries four times."""

    def __init__(self, *seconds: float) -> None:
        self._seconds = seconds

    def delay_after(self, attempt: int) -> float | None:
        return self._seconds[attempt - 1] if attempt <= len(self._seconds) else None


@dataclass(frozen=True)
class Exponential:
    """Doubles the wait after each failure, from `first` up to `cap` seconds."""

    first: float = 2
    cap: float = 300
    attempts: int = 5

    def __post_init__(self) -> None:
        if self.first <= 0 or self.cap < self.first or self.attempts < 1:
            raise ValueError("an exponential retry needs 0 < first <= cap and at least 1 attempt")

    def delay_after(self, attempt: int) -> float | None:
        if attempt >= self.attempts:
            return None
        return min(self.first * 2 ** (attempt - 1), self.cap)


# Tries once; a failure stops at once.
NO_RETRY = Delays()
