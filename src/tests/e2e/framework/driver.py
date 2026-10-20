"""Drives the app through the browser, as a user would. `get.*` returns what the user sees, for
assertions that wait until it appears (`expect(driver.get.header()).to_contain_text(...)`)."""

from playwright.sync_api import Locator, Page

from e2e.framework.system import APP_ORIGIN, Backend


class E2EDriver:
    def __init__(self, page: Page, backend: Backend) -> None:
        self.when = _When(page, backend)
        self.get = _Get(page)


class _When:
    def __init__(self, page: Page, backend: Backend) -> None:
        self._page = page
        self._backend = backend

    def open_the_app(self) -> None:
        self._page.goto(f"{APP_ORIGIN}/")

    def reload(self) -> None:
        self._page.reload()

    def sign_in_with_google(self) -> None:
        """Signs in again; with the debug user's token, the app signs in without Google."""
        self._page.get_by_role("button", name="Sign in with Google").click()

    def sign_out(self) -> None:
        self._page.get_by_role("button", name="Sign out").click()

    def restart_backend(self) -> None:
        self._backend.restart()


class _Get:
    def __init__(self, page: Page) -> None:
        self._page = page

    def header(self) -> Locator:
        return self._page.get_by_role("banner")

    def sign_in_button(self) -> Locator:
        return self._page.get_by_role("button", name="Sign in with Google")
