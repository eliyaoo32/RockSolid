"""Gives each test the whole system, on a fresh database, with the debug user signed in."""

from collections.abc import Iterator
from typing import Any

import pytest
from playwright.sync_api import Page

from e2e.framework.driver import E2EDriver
from e2e.framework.system import APP_ORIGIN, DEBUG_USER_JWT, running_backend, serve_the_app

# The frontend's key for the debug user's token (`DEBUG_USER_JWT_KEY` in debug-sign-in.ts).
DEBUG_USER_JWT_KEY = "rocksolid.debugUserJwt"


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args: dict[str, Any]) -> dict[str, Any]:
    """Uses the Google Chrome already installed, so no browser is downloaded."""
    return {**browser_type_launch_args, "channel": "chrome"}


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict[str, Any]) -> dict[str, Any]:
    """Starts every browser with the debug user's token, as if they had signed in before."""
    local_storage = [{"name": DEBUG_USER_JWT_KEY, "value": DEBUG_USER_JWT}]
    storage = {"cookies": [], "origins": [{"origin": APP_ORIGIN, "localStorage": local_storage}]}
    return {**browser_context_args, "storage_state": storage}


@pytest.fixture
def driver(database_url: str, page: Page) -> Iterator[E2EDriver]:
    with running_backend(database_url) as backend:
        serve_the_app(page.context, backend)
        yield E2EDriver(page, backend)
