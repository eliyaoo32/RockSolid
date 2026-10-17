from datetime import timedelta

from executables.clients_digest.tests.framework.driver import DigestDriver


async def test_logs_the_clients_created_in_the_last_day_every_morning(driver: DigestDriver) -> None:
    await driver.when.user_adds_clients("uid-dana", "Avi Cohen", "Noa Bar")
    await driver.when.user_adds_clients("uid-moshe", "Dana Levi")

    driver.when.time_passes(timedelta(hours=21, minutes=59))
    assert driver.get.digests() == [], "no digest before 07:00"

    driver.when.time_passes(timedelta(minutes=1))
    assert await driver.get.digests_once_there_are(1) == [3]

    driver.when.time_passes(timedelta(days=1))
    assert await driver.get.digests_once_there_are(2) == [3, 0]
