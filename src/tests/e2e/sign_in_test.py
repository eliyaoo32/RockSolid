from playwright.sync_api import expect

from e2e.framework.driver import E2EDriver
from e2e.framework.system import DEBUG_USER_NAME


def test_shows_the_signed_in_user_across_a_reload_and_signs_out_and_back_in(
    driver: E2EDriver,
) -> None:
    driver.when.open_the_app()
    # The name comes from the backend, which signed in its debug user from the browser's token.
    expect(driver.get.header()).to_contain_text(DEBUG_USER_NAME)

    driver.when.reload()
    expect(driver.get.header()).to_contain_text(DEBUG_USER_NAME)

    driver.when.sign_out()
    expect(driver.get.sign_in_button()).to_be_visible()

    driver.when.sign_in_with_google()
    expect(driver.get.header()).to_contain_text(DEBUG_USER_NAME)


def test_keeps_the_user_signed_in_across_a_backend_restart(driver: E2EDriver) -> None:
    driver.when.open_the_app()
    expect(driver.get.header()).to_contain_text(DEBUG_USER_NAME)

    driver.when.restart_backend()
    driver.when.reload()

    expect(driver.get.header()).to_contain_text(DEBUG_USER_NAME)
