import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from libs.testing.time import FakeTime, eventually

START = datetime(2026, 10, 17, 9, 0, tzinfo=UTC)


async def test_fake_time_returns_at_once_for_a_time_already_passed() -> None:
    time = FakeTime(START)

    async with asyncio.timeout(1):
        await time.wait(START - timedelta(minutes=1), asyncio.Event())


async def test_eventually_checks_again_until_the_check_passes() -> None:
    answers = iter([False, False, True])

    await eventually(lambda: next(answers))

    assert next(answers, "every answer used") == "every answer used"


async def test_eventually_awaits_an_async_check() -> None:
    async def ready() -> bool:
        return True

    await eventually(ready)


async def test_eventually_fails_when_the_check_never_passes() -> None:
    with pytest.raises(TimeoutError):
        await eventually(lambda: False, timeout=0.05)
