from executables.client_activity.tests.framework.driver import ActivityDriver


async def test_logs_each_client_created_without_its_name(driver: ActivityDriver) -> None:
    avi = await driver.when.user_adds_client("uid-dana", "Avi Cohen")
    noa = await driver.when.user_adds_client("uid-moshe", "Noa Bar")

    assert await driver.get.activity_once_it_has(2) == [
        (str(avi), "uid-dana"),
        (str(noa), "uid-moshe"),
    ]
    assert "Avi Cohen" not in driver.get.text(), "names are personal data, never logged"
