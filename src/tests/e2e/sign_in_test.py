from playwright.sync_api import expect

from e2e.framework.driver import E2EDriver
from e2e.framework.system import DEBUG_USER_NAME


def test_shows_the_signed_in_user_across_a_reload_and_stays_signed_out_after_signing_out(
    driver: E2EDriver,
) -> None:
    driver.when.open_the_app()
    # The backend's name for the user, so the backend signed in the debug user from its token.
    expect(driver.get.account()).to_contain_text(DEBUG_USER_NAME)

    driver.when.reload()
    expect(driver.get.account()).to_contain_text(DEBUG_USER_NAME)

    driver.when.sign_out()
    expect(driver.get.sign_in_button()).to_be_visible()

    driver.when.reload()
    expect(driver.get.sign_in_button()).to_be_visible()


def test_keeps_the_user_signed_in_across_a_backend_restart(driver: E2EDriver) -> None:
    driver.when.open_the_app()
    expect(driver.get.account()).to_contain_text(DEBUG_USER_NAME)

    driver.when.restart_the_backend()
    driver.when.reload()

    expect(driver.get.account()).to_contain_text(DEBUG_USER_NAME)
