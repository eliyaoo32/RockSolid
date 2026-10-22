"""Sign-in for tests, in place of Firebase."""

from modules.users.domain.user import User
from modules.users.services.auth import Auth


class FakeUsers:
    """Signs in `token-<user id>` as that user, and no other token."""

    async def from_token(self, token: str) -> User | None:
        if not token.startswith("token-"):
            return None
        user_id = token.removeprefix("token-")
        return User(id=user_id, email=f"{user_id}@example.com", display_name=user_id)


def fake_auth() -> Auth:
    """Signs callers in with `token-<user id>`."""
    return Auth(FakeUsers())
