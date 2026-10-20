"""Gives each test the whole system, on a fresh database, with the debug user signed in."""

import json
from collections.abc import Iterator
from typing import Any

import pytest
from playwright.sync_api import Page

from e2e.framework.driver import E2EDriver
from e2e.framework.system import (
    APP_ORIGIN,
    DEBUG_USER,
    DEBUG_USER_JWT,
    FIREBASE_API_KEY,
    running_system,
    serve_the_app,
)

# Far in the future (year 2109, in milliseconds), so the Firebase SDK never refreshes the token.
EXPIRES_LATER_MS = 2**42


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args: dict[str, Any]) -> dict[str, Any]:
    """Uses the Google Chrome already installed, so no browser is downloaded."""
    return {**browser_type_launch_args, "channel": "chrome"}


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict[str, Any]) -> dict[str, Any]:
    """Starts every browser signed in as the debug user, as the Firebase SDK keeps a user who
    signed in before, with the debug user's token as the ID token."""
    session: dict[str, object] = {
        "uid": DEBUG_USER["localId"],
        "email": DEBUG_USER["email"],
        "emailVerified": True,
        "displayName": DEBUG_USER["displayName"],
        "isAnonymous": False,
        "providerData": [],
        "stsTokenManager": {
            "refreshToken": "e2e-refresh-token",
            "accessToken": DEBUG_USER_JWT,
            "expirationTime": EXPIRES_LATER_MS,
        },
        "createdAt": "0",
        "lastLoginAt": "0",
        "apiKey": FIREBASE_API_KEY,
        "appName": "[DEFAULT]",
    }
    item = {"name": f"firebase:authUser:{FIREBASE_API_KEY}:[DEFAULT]", "value": json.dumps(session)}
    storage = {"cookies": [], "origins": [{"origin": APP_ORIGIN, "localStorage": [item]}]}
    return {**browser_context_args, "storage_state": storage}


@pytest.fixture
def driver(database_url: str, page: Page) -> Iterator[E2EDriver]:
    with running_system(database_url) as system:
        serve_the_app(page.context, system)
        yield E2EDriver(page, system)
