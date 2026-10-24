"""Drives the app through the browser, as a user would. `get.*` returns what the user sees, for
assertions that wait until it appears (`expect(driver.get.account()).to_contain_text(...)`).

It finds controls by `data-testid`, never by their text or layout, so it drives every project's
own sign-in and account controls, in any language."""

from playwright.sync_api import Locator, Page

from e2e.framework.system import APP_ORIGIN, System


class E2EDriver:
    def __init__(self, page: Page, system: System) -> None:
        self.when = _When(page, system)
        self.get = _Get(page)


class _When:
    def __init__(self, page: Page, system: System) -> None:
        self._page = page
        self._system = system

    def open_the_app(self) -> None:
        self._page.goto(f"{APP_ORIGIN}/")

    def reload(self) -> None:
        self._page.reload()

    def sign_out(self) -> None:
        # The account control opens the menu that holds sign-out, when a project keeps it in one.
        self._page.get_by_test_id("account").click()
        self._page.get_by_test_id("sign-out").click()

    def restart_the_backend(self) -> None:
        """Restarts every deployable, as a release does."""
        self._system.restart()


class _Get:
    def __init__(self, page: Page) -> None:
        self._page = page

    def account(self) -> Locator:
        """The control that shows the signed-in user's name."""
        return self._page.get_by_test_id("account")

    def sign_in_button(self) -> Locator:
        return self._page.get_by_test_id("sign-in-with-google")
