"""Signs in one configured user, in place of Firebase, where the backend runs with `DEBUG=true`
and `DEBUG_USER_JWT` set, such as in E2E tests. Any other token signs in nobody."""

import hmac

from modules.users.domain.user import User

DEBUG_USER_ID = "debug-user"


class DebugUserRepository:
    def __init__(self, token: str, display_name: str) -> None:
        self._token = token
        self._user = User(
            id=DEBUG_USER_ID, email=f"{DEBUG_USER_ID}@example.com", display_name=display_name
        )

    async def from_token(self, token: str) -> User | None:
        same = hmac.compare_digest(token.encode(), self._token.encode())
        return self._user if same else None
