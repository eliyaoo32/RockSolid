from executables.client_welcome.tests.framework.driver import WelcomeDriver


async def test_welcomes_each_new_client_who_has_an_email_address(driver: WelcomeDriver) -> None:
    await driver.when.user_adds_client("uid-dana", "Noa Bar", email=None)
    avi = await driver.when.user_adds_client("uid-dana", "Avi Cohen", email="avi@example.com")
    dana = await driver.when.user_adds_client("uid-moshe", "Dana Levi", email="dana@example.com")

    assert await driver.get.welcomes_once_there_are(2) == [
        (str(avi), "uid-dana"),
        (str(dana), "uid-moshe"),
    ], "Noa has no email address, so she is not welcomed"
    assert await driver.get.every_task_ran(), "no welcome is left waiting"
    assert "avi@example.com" not in driver.get.text(), "email addresses are never logged"
