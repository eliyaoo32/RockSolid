from e2e.framework.fakes.mail_api import API_KEY
from executables.client_welcome.tests.framework.driver import WelcomeDriver


async def test_welcomes_each_new_client_who_has_an_email_address(driver: WelcomeDriver) -> None:
    await driver.when.user_adds_client("uid-dana", "Noa Bar", email=None)
    avi = await driver.when.user_adds_client("uid-dana", "Avi Cohen", email="avi@example.com")
    await driver.when.user_adds_client("uid-moshe", "Dana Levi", email="dana@example.com")

    assert await driver.get.welcomes_once_there_are(2) == [
        ("avi@example.com", "Avi Cohen"),
        ("dana@example.com", "Dana Levi"),
    ], "Noa has no email address, so she is not welcomed"
    assert driver.get.messages()[0] == (
        "/v1/messages",
        f"Bearer {API_KEY}",
        {
            "to": "avi@example.com",
            "template": "client-welcome",
            "variables": {"name": "Avi Cohen"},
            "idempotency_key": str(avi),
        },
    ), "the welcome reaches the mail API the settings point at, signed with its key"
    assert await driver.get.every_task_ran(), "no welcome is left waiting"
    assert "avi@example.com" not in driver.get.text(), "email addresses are never logged"


async def test_retries_a_welcome_the_mail_api_failed_unless_the_client_was_deleted_meanwhile(
    driver: WelcomeDriver,
) -> None:
    driver.when.mail_api_fails_next(2)
    await driver.when.user_adds_client("uid-dana", "Avi Cohen", email="avi@example.com")
    dana = await driver.when.user_adds_client("uid-moshe", "Dana Levi", email="dana@example.com")
    assert await driver.get.failed_welcomes_once_there_are(2) == 2
    assert driver.get.welcomes() == [], "the mail API sent nothing while it failed"

    await driver.when.user_deletes_client("uid-moshe", dana)
    driver.when.time_passes(seconds=2)

    assert await driver.get.welcomes_once_there_are(1) == [("avi@example.com", "Avi Cohen")]
    assert await driver.get.every_task_ran(), "Dana's welcome ran and found her deleted"
    assert driver.get.welcomes() == [("avi@example.com", "Avi Cohen")], "Dana is not welcomed"


async def test_parks_the_welcome_when_the_mail_api_key_is_not_set(
    driver_without_mail_api_key: WelcomeDriver,
) -> None:
    driver = driver_without_mail_api_key
    await driver.when.user_adds_client("uid-dana", "Avi Cohen", email="avi@example.com")

    assert await driver.get.parked_welcomes_once_there_are(1) == 1, "a retry cannot set the key"
    assert driver.get.welcomes() == []
